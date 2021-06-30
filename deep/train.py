from typing import List

from torch import optim

from simulation.base.terrain import Inspectable
from .constants import *
from .policy import Policy
from .env import Env


def ensure_shared_grads(model, shared_model):
    for param, shared_param in zip(model.parameters(),
                                   shared_model.parameters()):
        if shared_param.grad is not None:
            return
        shared_param._grad = param.grad


def env_step(model, optimizer, env, state, lstm_parameters):
    # value is a prediction of the value of the environment at a specific point.
    # action_prediction is used to determine action which is passed to next step.
    # IT IS ALSO USED TO DETERMINE ENTROPY used for policy loss.
    #
    # We first predict the action and value for this specific state.
    hn, cn = lstm_parameters
    action_prediction, value_prediction, (hn, cn) = model(state, (hn, cn))

    # We apply multinomial to all action keys except destroy_slots.
    multinomial_action_prediction = {}
    for key in action_prediction:
        if key != "destroy_slots":
            multinomial_action_prediction[key] = action_prediction[key].multinomial(1)
        else:
            multinomial_action_prediction[key] = action_prediction[key]

    # We apply that action to our environment and take note of how it changes.
    no_grad_action_prediction = {k: multinomial_action_prediction[k].detach() for k in multinomial_action_prediction}
    state, reward, done, action_string, last_tick = env.step(no_grad_action_prediction)

    if done and (last_tick < Inspectable.WAVE - 5):
        debug("deep.train", "The model finished a wave, so we're saving it.")
        torch.save({
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
        }, "wave_finish.checkpoint")

    # we calculate log probabilities of predictions as well as entropies.
    log_predictions = {}
    entropies = {}
    for key in multinomial_action_prediction:
        # We don't want losses for irrelevant action keys.
        # TODO: Fix this to mask in the policy model itself, by supplying it an input of "available actions".
        #  Action should be masked based on role.
        #  -- Fire egg should only be there if player is interacting with cannon.
        #  -- Repair trap should only be there if player is defender and trap isn't full.
        #  Target should be masked based on action (has to be pick food or use poison).
        #  -- and on available targets (healers / foods) within sight.
        #  Moves (x and y) should be masked based on action (has to be move) and on tile pathability.
        #  Drop count should be masked based on current correct call food count in inventory, and obviously on role (D).
        #  Destroy slots is the fucked up sigmoid. It should be masked based on whether that inventory slot has a food.
        #  Dispenser option should be masked on action (has to be use dispenser) and on role (H).
        #  Egg target should be masked based on action (has to be fire egg, a pretty rare action).
        if action_string != "click_move" and (key == "move_x" or key == "move_y"):
            continue
        if action_string != "click_pick_item" and action_string != "click_use_poison_food" and key == "target":
            continue
        if action_string != "click_fire_egg" and key == "egg_target":
            continue

        # The log predictions for destroy_slots do not sum to one,
        # each is an individual probability that's binary-entropy (to do, or not to do),
        # and does not compete with the others.
        if key != "destroy_slots":
            probable_action = action_prediction[key].gather(1, multinomial_action_prediction[key]).clamp(min=1e-6)
            log_predictions[key] = torch.log(probable_action)
            entropies[key] = log_predictions[key] * probable_action
        else:
            # They get summed in policy loss anyway, so it's okay to sum them here.
            probable_actions = action_prediction[key][action_prediction[key] > DESTROY_PROBABILITY]
            log_predictions[key] = torch.sum(torch.log(probable_actions)).view(1, 1)
            entropies[key] = torch.sum(log_predictions[key] * probable_actions).view(1, 1)

    return state, (hn, cn), done, reward, value_prediction, (log_predictions, entropies)


# We have 2 losses.
# The value loss. This is half the sum of the squares of the advantages.
# Why?
#
# The reward loss (we back-prop on policy actions, trying to increase the cumulative reward of following the policy).
# The reward loss is given by sum(-log(π(a_t))A(a_t) + α * -log(π(a_t))π(a_t), t)
# The entropy term (starting alpha) guarantees that my actions probabilities have either too high a chance or
# too low a chance, to prevent the model from giving all actions probabilities around 50%.
# The advantage term gives loss which makes positive advantage actions happening at high probability and
# negative advantage actions happening at low probability more favorable than otherwise.
#
# π(a_t) is simply the probability of the action a at time t as given by the policy π.
# The advantage, A, is given by R(s_t) - V(s_t) (where t is the time since the trajectory started).
# Here, R(s_t) is the calculated discounted cumulative return upto this time-point,
# and V(s_t) is the critic-emitted value prediction (from the policy network).
def train(rank, shared_model, counter, lock, optimizer, device):
    torch.manual_seed(SEED + rank)
    env = Env("d", CUDA0)
    model = Policy().to(device)
    model.train()

    if optimizer is None:
        optimizer = optim.Adam(shared_model.parameters(), lr=LEARNING_RATE)

    # The initial values for looping.
    (hn, cn) = (torch.zeros(LSTM_HIDDEN_SIZE, device=device), torch.zeros(LSTM_HIDDEN_SIZE, device=device))
    state = env.reset()
    done = True

    for iteration in range(ITERATION_COUNT):
        model.load_state_dict(shared_model.state_dict())

        if done:
            (hn, cn) = (torch.zeros(LSTM_HIDDEN_SIZE, device=device), torch.zeros(LSTM_HIDDEN_SIZE, device=device))
        else:
            hn.detach_()
            cn.detach_()

        value_predictions = torch.zeros((NUM_FORWARD_STEPS_PER_TRAJECTORY + 1, 1, 1), device=device)
        rewards = torch.zeros((NUM_FORWARD_STEPS_PER_TRAJECTORY, 1, 1), device=device)
        loss_stuff: List[Optional[Tuple[torch.Tensor, torch.Tensor]]] = [None] * NUM_FORWARD_STEPS_PER_TRAJECTORY

        end_index = NUM_FORWARD_STEPS_PER_TRAJECTORY

        # We explore a trajectory of NUM_FORWARD_STEPS_PER_TRAJECTORY time steps,
        # taking note of the values and value predictions for back-propagating
        # through the value prediction network.
        for j in range(NUM_FORWARD_STEPS_PER_TRAJECTORY):
            state, (hn, cn), done, rewards[j], value_predictions[j], loss_stuff[j] = \
                env_step(model, optimizer, env, state, (hn, cn))

            with lock:
                counter.value += 1

            if done:
                state = env.reset()
                end_index = j
                break

        # We calculate our discounted cumulative return, and from it, the advantages.
        # then finally, the losses.
        discounted_cumulative_return = torch.zeros((1, 1), device=device)
        gae = torch.zeros((1, 1), device=device)
        policy_loss = torch.zeros((1, 1), device=device)
        value_loss = torch.zeros((1, 1), device=device)

        # If we're not done, we run the model forward one last time.
        # We set the initial value of the discounted cumulative return to the value prediction.
        # Why?
        #
        # We also need that extra prediction because in GAE below, we need access to
        # value_predictions[j + 1], which we do not have if we only did j attempts.
        if not done:
            state_copy = state.copy()
            _, value_prediction, _ = model(state, (hn, cn))
            state = state_copy
            discounted_cumulative_return += value_prediction.detach()

        value_predictions[end_index] = discounted_cumulative_return

        for j in range(end_index - 1, -1, -1):
            discounted_cumulative_return = DISCOUNT_FACTOR * discounted_cumulative_return + rewards[j]
            advantage = discounted_cumulative_return - value_predictions[j]
            value_loss = value_loss + VALUE_LOSS_WEIGHT * advantage.pow(2)

            # Generalized Advantage Estimation
            td_residual_discounted_sum = rewards[j] + DISCOUNT_FACTOR * value_predictions[j + 1] - value_predictions[j]
            gae = DISCOUNT_FACTOR * gae * GAE_PARAMETER + td_residual_discounted_sum

            log_predictions, entropies = loss_stuff[j]
            for key in log_predictions:
                policy_loss += -(log_predictions[key] * gae.detach() + ENTROPY_WEIGHT * entropies[key])

        if iteration % ITERATIONS_PER_LOG == 0:
            debug("deep.train", f"value_loss = {value_loss}, policy_loss = {policy_loss}")

        optimizer.zero_grad()
        (policy_loss + VALUE_LOSS_WEIGHT * value_loss).backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), MAX_GRAD_NORM)
        ensure_shared_grads(model, shared_model)
        optimizer.step()
