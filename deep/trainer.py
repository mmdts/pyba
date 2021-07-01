from datetime import datetime
from typing import List

from torch.optim import Optimizer
from torch.types import Device
import torch.multiprocessing as mp
from torch import optim

from simulation.base.terrain import Inspectable
from .constants import *
from .policy import Policy
from .env import Env


class Trainer:
    def __init__(
        self, rank: int, shared_model: Policy, counter: mp.Value, lock: mp.Lock,
        optimizer: Optional[Optimizer], device: Device
    ):
        torch.manual_seed(SEED + rank)
        self.env: Env = Env("d", device)
        self.model: Policy = Policy().to(device)
        self.model.train()

        self.device: Device = device
        self.shared_model: Policy = shared_model
        self.counter: mp.Value = counter
        self.lock: mp.Lock = lock

        self.optimizer: Optimizer = optimizer
        if optimizer is None:
            self.optimizer: Optimizer = optim.Adam(shared_model.parameters(), lr=LEARNING_RATE)

        self.hidden: Hidden = self.init_hidden()

        self.state: Optional[State] = None
        self.masks: Optional[Masks] = None
        self.state, self.masks = self.env.reset()

        self.done: bool = True

    def __call__(self) -> None:
        for iteration in range(ITERATION_COUNT):
            self.model.load_state_dict(self.shared_model.state_dict())

            if self.done:
                self.init_hidden()
            else:
                self.detach_hidden()

            rewards: torch.Tensor = torch.zeros((NUM_FORWARD_STEPS_PER_TRAJECTORY, 1, 1), device=self.device)
            p_critics: torch.Tensor = torch.zeros((NUM_FORWARD_STEPS_PER_TRAJECTORY + 1, 1, 1), device=self.device)
            # Loss stuff is log probabilities and entropies used for loss calculation.
            loss_stuff: List[Optional[Tuple[Prediction, Prediction]]] = [None] * NUM_FORWARD_STEPS_PER_TRAJECTORY

            end_index: int = NUM_FORWARD_STEPS_PER_TRAJECTORY

            # We explore a trajectory of NUM_FORWARD_STEPS_PER_TRAJECTORY time steps,
            # taking note of the values and value predictions for back-propagating
            # through the value prediction network.
            for j in range(NUM_FORWARD_STEPS_PER_TRAJECTORY):
                rewards[j], p_critics[j], loss_stuff[j] = self.env_step()

                with self.lock:
                    self.counter.value += 1

                if self.done:
                    self.state, self.masks = self.env.reset()
                    end_index = j
                    break

            # We calculate our discounted cumulative return, and from it, the advantages.
            # then finally, the losses.
            discounted_cumulative_return: torch.Tensor = torch.zeros((1, 1), device=self.device)
            gae: torch.Tensor = torch.zeros((1, 1), device=self.device)
            actor_loss: torch.Tensor = torch.zeros((1, 1), device=self.device)
            critic_loss: torch.Tensor = torch.zeros((1, 1), device=self.device)

            # If we're not done, we run the model forward one last time.
            # We set the initial value of the discounted cumulative return to the value prediction.
            # Why?
            #
            # We also need that extra prediction because in GAE below, we need access to
            # p_values[j + 1], which we do not have if we only did j attempts.
            if not self.done:
                _, p_critic, _ = self.run_model()
                discounted_cumulative_return += p_critic.detach()

            p_critics[end_index] = discounted_cumulative_return

            for j in range(end_index - 1, -1, -1):
                discounted_cumulative_return = DISCOUNT_FACTOR * discounted_cumulative_return + rewards[j]
                advantage = discounted_cumulative_return - p_critics[j]
                critic_loss += CRITIC_LOSS_WEIGHT * advantage.pow(2)

                # Generalized Advantage Estimation
                td_residual_disc_sum = rewards[j] + DISCOUNT_FACTOR * p_critics[j + 1] - p_critics[j]
                gae = DISCOUNT_FACTOR * gae * GAE_PARAMETER + td_residual_disc_sum

                log_p_actor, entropy = loss_stuff[j]
                for key in log_p_actor:
                    actor_loss += -(log_p_actor[key] * gae.detach() + ENTROPY_WEIGHT * entropy[key])

            if iteration % ITERATIONS_PER_LOG == 0:
                debug("deep.train", f"critic_loss = {critic_loss}, actor_loss = {actor_loss}")

            self.optimizer.zero_grad()
            (actor_loss + CRITIC_LOSS_WEIGHT * critic_loss).backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), MAX_GRAD_NORM)
            self.ensure_shared_grads()
            self.optimizer.step()

    def init_hidden(self) -> Hidden:
        self.hidden = (torch.zeros(LSTM_HIDDEN_SIZE, device=self.device),
                       torch.zeros(LSTM_HIDDEN_SIZE, device=self.device))
        return self.hidden

    def detach_hidden(self) -> None:
        hn, cn = self.hidden
        hn.detach_()
        cn.detach_()

    def run_model(self) -> Tuple[Prediction, torch.Tensor, Hidden]:
        return self.model(self.state, self.hidden)

    def save_model(self, debug_str: str) -> None:
        debug("deep.train", debug_str, datetime.now())
        torch.save({
            "model": self.model.state_dict(),
            "optimizer": self.optimizer.state_dict(),
        }, "wave_finish.checkpoint")

    @staticmethod
    def get_p_actor_multinomial(p_actor: Prediction, picked_action_multinomial: torch.Tensor) -> Prediction:
        # The multinomial action prediction may have less keys than the action prediction.
        # All calculations after the point at which this function will applied will use the
        # keys from the multinomial action prediction.
        p_actor_multinomial = {}
        for key in p_actor:
            # We do not calculate multinomial actions for keys that got completely masked.
            if p_actor[key].sum(dim=1) < 0.5:
                continue

            # We don't re-pick an action. One was already picked in Trainer.pick_action to allow us to mask things.
            if key == "action":
                p_actor_multinomial[key] = picked_action_multinomial
                continue

            # We apply multinomial to all action keys except destroy_slots.
            if key != "destroy_slots":
                p_actor_multinomial[key] = p_actor[key].multinomial(1)
            else:
                probable_destroys = p_actor[key] * (p_actor[key] > DESTROY_PROBABILITY)

                # We don't add this key if there's nothing probable to destroy.
                if probable_destroys.sum() < 0.5:
                    continue

                p_actor_multinomial[key] = probable_destroys

        return p_actor_multinomial

    @staticmethod
    def get_loss_stuff(p_actor: Prediction, p_actor_multinomial: Prediction) -> Tuple[Prediction, Prediction]:
        # Only keys that get put forward in log_predictions and entropies and thus get used in back propagation.
        # We filter everything tht got masked out here in an environment-agnostic way.
        #
        # The real environment-related filtering happens during the mask-building in build_emittable_object_from,
        # then in Trainer.mask_output.
        log_p_actors = {}
        entropies = {}
        # We don't want losses for irrelevant action keys, so we only use the keys of p_actor_multinomial.
        for key in p_actor_multinomial:
            # The log predictions for destroy_slots do not sum to one,
            # each is an individual probability that's binary-entropy (to do, or not to do),
            # and does not compete with the others.
            if key != "destroy_slots":
                probable_action = p_actor[key].gather(1, p_actor_multinomial[key]).clamp(min=1e-6)
                log_p_actors[key] = torch.log(probable_action)
                entropies[key] = log_p_actors[key] * probable_action
            else:
                # They get summed in policy loss anyway, so it's okay to sum them here.
                log_p_actors[key] = torch.log(p_actor_multinomial[key]).sum(dim=1)
                entropies[key] = log_p_actors[key] * p_actor_multinomial[key].sum(dim=1)

        return log_p_actors, entropies

    def pick_action(self, p_actor: Prediction) -> torch.Tensor:
        # Action masking happens here.
        # We mask the action before anything else, so that we can filter p_actor based on it in the
        # if conditions at the start of Trainer.mask_p_actor.
        p_actor["action"] = p_actor["action"] * self.masks["action"]
        p_actor["action"] = p_actor["action"] / p_actor["action"].sum(dim=1)

        return p_actor["action"].multinomial(1)

    def mask_p_actor(self, p_actor: Prediction, picked_action_multinomial: torch.Tensor) -> Prediction:
        action = Env.ACTIONS[picked_action_multinomial.cpu().item()]
        if action != "click_move":
            p_actor["move"] = p_actor["move"] * 0
        if action != "click_pick_item" and action != "click_use_poison_food":
            p_actor["target"] = p_actor["target"] * 0
        if action != "click_fire_egg":
            p_actor["egg_target"] = p_actor["egg_target"] * 0
        if action != "click_use_dispenser" or self.env.role != "h":
            p_actor["dispenser_option"] = p_actor["dispenser_option"] * 0

        for key in p_actor:
            # We leave p_actor keys not in self.masks alone.
            # We leave the key "action" alone since that was already filtered in Trainer.pick_action.
            if key not in self.masks or key == "action":
                continue

            # We discard the entire tensor if the mask discards it.
            if self.masks[key].sum(dim=1) < 0.5:
                p_actor[key] = p_actor[key] * 0

            # We do not calculate masks for keys we have already discarded.
            if p_actor[key].sum(dim=1) < 0.5:
                continue

            p_actor[key] = p_actor[key] * self.masks[key]

            # We normalize everything to sum back up to 1, except destroy slots with is a sigmoid not a softmax.
            if key != "destroy_slots":
                p_actor[key] /= p_actor[key].sum(dim=1)

        return p_actor

    def env_step(self) -> Tuple[torch.Tensor, torch.Tensor, Tuple[Prediction, Prediction]]:
        # value is a prediction of the value of the environment at a specific point.
        # p_action is used to determine action which is passed to next step.
        # It is also used to determine entropy used for policy loss.
        #
        # We first predict the action and value for this specific state.
        p_actor, p_critic, self.hidden = self.run_model()

        # Action is chosen here, for consistency (so multinomial only happens once, and picks something once).
        picked_action_multinomial = self.pick_action(p_actor)
        # We mask the actor using the masks calculated from self.env.step in the last call of self.env_step.
        p_actor = self.mask_p_actor(p_actor, picked_action_multinomial)

        # We then calculate multinomial actor predictions for use in deciding keys
        # relevant to log probabilities and entropies for loss calculation,
        p_actor_multinomial = Trainer.get_p_actor_multinomial(p_actor, picked_action_multinomial)

        debug("Env.step", f"====================================================================")
        debug("Env.step", f"Possible actions were: {p_actor['action'].detach().cpu().numpy()}")
        debug("Env.step", f"Final multinomial dict keys: {p_actor_multinomial.keys()}")

        # We calculate nograd actor predictions for use in environment stepping, then,
        # We apply that action to our environment and take note of how it changes.
        p_actor_nograd = {k: p_actor_multinomial[k].detach() for k in p_actor_multinomial}

        self.state, self.masks, reward, self.done, last_tick = self.env.step(p_actor_nograd, picked_action_multinomial)

        debug("Env.step", f"====================================================================")

        if self.done and (last_tick < Inspectable.WAVE - 5):
            self.save_model("The model finished a wave, so we're saving it.")

        # We calculate log probabilities of predictions as well as entropies, and return everything.
        return reward, p_critic, self.get_loss_stuff(p_actor, p_actor_multinomial)

    def ensure_shared_grads(self):
        for param, shared_param in zip(self.model.parameters(), self.shared_model.parameters()):
            if shared_param.grad is not None:
                return
            shared_param._grad = param.grad
