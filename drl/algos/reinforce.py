#!/usr/bin/env python

import torch as th
import torch.nn.functional as F
from torch import Tensor as T
from torch.autograd import Variable as V
from torch.autograd import backward
from math import pi, exp

from .base import BaseAgent
from .algos_utils import discount, normalize, EPSILON

from ..models import ConstantCritic


class Reinforce(BaseAgent):

    def __init__(self, policy=None, critic=None, gamma=0.99, update_frequency=1000, entropy_weight=0.0001, critic_weight=0.5,
                 grad_clip=50.0):
        self.policy = policy
        self.gamma = gamma
        if critic is None:
            critic = ConstantCritic(0)
        self.critic = critic
        self.entropy_weight = entropy_weight
        self.critic_weight = critic_weight
        self.update_frequency = update_frequency
        self.grad_clip = grad_clip
        self._reset()

    def _reset(self):
        self.steps = 0
        self.rewards = [[], ]
        self.entropies = [[], ]
        self.actions = [[], ]
        self.critics = [[], ]

    def parameters(self):
        return self.policy.parameters()

    def _variable(self, state):
        state = th.from_numpy(state).float()
        if len(state.size()) < 2:
            state = state.unsqueeze(0)
        return V(state)

    def act(self, state):
        state = self._variable(state)
        action = self.policy(state)
        return action.value[0], action

    def learn(self, state, action, reward, next_state, done, info=None):
        self.rewards[-1].append(reward)
        self.actions[-1].append(info.log_sampled)
        self.critics[-1].append(self.critic(self._variable(state)))
        self.steps += 1

    def new_episode(self, terminated=False):
        self.rewards.append([])
        self.actions.append([])
        self.critics.append([])

    def get_update(self):
        """
        TODO:
            * entropy
            * lstm
        """
        for actions_ep, rewards_ep, critics_ep in zip(self.actions, self.rewards, self.critics):
            if len(actions_ep) > 0:
                rewards = discount(rewards_ep, self.gamma)
                rewards = normalize(rewards)
                policy_loss = 0.0
                critic_loss = 0.0
                for action, r, critic in zip(actions_ep, rewards, critics_ep):
                    advantage = V(T([r])) - critic
                    policy_loss = policy_loss - action.sum() * advantage.data[0, 0]
                    critic_loss = critic_loss + advantage.pow(2)
                loss = policy_loss + self.critic_weight * critic_loss
                loss.backward()
                th.nn.utils.clip_grad_norm(self.parameters(), self.grad_clip)
        self._reset()
        return [p.grad.clone() for p in self.parameters()]

    def updatable(self):
        if self.update_frequency > 0:
            if self.steps >= self.update_frequency:
                return True
        else:
            if len(self.actions) > 1:
                return True
        return False
