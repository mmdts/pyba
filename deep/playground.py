from typing import Tuple, List

from torch import optim
from .constants import *
from .policy import Policy
from .env import Env


def ensure_shared_grads(model, shared_model):
    for param, shared_param in zip(model.parameters(),
                                   shared_model.parameters()):
        if shared_param.grad is not None:
            return
        shared_param._grad = param.grad


def env_step(model, env, state, lstm_parameters):
    # value is a prediction of the value of the environment at a specific point.
    # action_prediction is used to determine action which is passed to next step.
    # IT IS ALSO USED TO DETERMINE ENTROPY used for policy loss.
    #
    # We first predict the action and value for this specific state.
    hn, cn = lstm_parameters
    action_prediction, value_prediction, (hn, cn) = model(state, (hn, cn))

    # We apply that action to our environment and take note of how it changes.
    no_grad_action_prediction = {k: action_prediction[k].detach() for k in action_prediction}
    state, reward, done, action_string = env.step(no_grad_action_prediction)

    log_predictions = {}
    entropies = {}
    for key in action_prediction:
        # We don't want losses for irrelevant action keys.
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
            probable_action = torch.max(action_prediction[key])
        else:
            probable_action = torch.sum((action_prediction[key] > DESTROY_PROBABILITY) * action_prediction[key])

        log_predictions[key] = torch.log(probable_action).clamp(min=-100)
        entropies[key] = log_predictions[key] * probable_action

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
def train(checkpoint, device):
    model = Policy().to(device)

    if checkpoint is not None:
        model.load_state_dict(torch.load(checkpoint))

    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    env = Env("d", device)

    # The initial values for looping.
    (hn, cn) = (torch.zeros((1, 512), device=device), torch.zeros((1, 512), device=device))
    state = env.reset()

    done = False

    for iteration in range(ITERATION_COUNT):
        value_predictions = torch.zeros((NUM_FORWARD_STEPS_PER_TRAJECTORY + 1, 1, 1), device=device)
        rewards = torch.zeros((NUM_FORWARD_STEPS_PER_TRAJECTORY, 1, 1), device=device)
        advantages = torch.zeros((NUM_FORWARD_STEPS_PER_TRAJECTORY, 1, 1), device=device)
        loss_stuff: List[Optional[Tuple[torch.Tensor, torch.Tensor]]] = [None] * NUM_FORWARD_STEPS_PER_TRAJECTORY

        end_index = NUM_FORWARD_STEPS_PER_TRAJECTORY

        # We explore a trajectory of NUM_FORWARD_STEPS_PER_TRAJECTORY time steps,
        # taking note of the values and value predictions for back-propagating
        # through the value prediction network.
        for j in range(NUM_FORWARD_STEPS_PER_TRAJECTORY):
            state, (hn, cn), done, rewards[j], value_predictions[j], loss_stuff[j] = env_step(model, env, state, (hn, cn))
            if done:
                end_index = j
                break

        if done:
            (hn, cn) = (torch.zeros((1, 512), device=device), torch.zeros((1, 512), device=device))
            state = env.reset()

        # We calculate our discounted cumulative return, and from it, the advantages.
        # then finally, the losses.
        discounted_cumulative_return = torch.zeros((1, 1), device=device)
        advantage_estimation = torch.zeros((1, 1), device=device)
        policy_loss = torch.zeros((1, 1), device=device)

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
            discounted_cumulative_return += value_prediction

        value_predictions[end_index] = discounted_cumulative_return

        for j in range(end_index - 1, -1, -1):
            discounted_cumulative_return = DISCOUNT_FACTOR * discounted_cumulative_return + rewards[j]

            advantages[j] = discounted_cumulative_return - value_predictions[j]

            # Generalized Advantage Estimation
            delta_t = rewards[j] + DISCOUNT_FACTOR * value_predictions[j + 1] - value_predictions[j]
            advantage_estimation = DISCOUNT_FACTOR * advantage_estimation * GAE_PARAMETER + delta_t

            log_predictions, entropies = loss_stuff[j]
            for key in log_predictions:
                policy_loss = policy_loss \
                              - log_predictions[key] * advantage_estimation \
                              - ENTROPY_WEIGHT * entropies[key]

        value_loss = 0.5 * torch.sum(advantages, dim=0).pow(2)

        debug("General", f"value_loss = {value_loss}, policy_loss = {policy_loss}")

        optimizer.zero_grad()
        (policy_loss + 0.5 * value_loss).backward()
        # torch.nn.utils.clip_grad_norm_(model.parameters(), 40, error_if_nonfinite=False)
        optimizer.step()
