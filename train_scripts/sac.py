import datetime
import os
import shutil
from argparse import ArgumentParser

import yaml
from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import EvalCallback
from stable_baselines3.common.utils import set_random_seed
from stable_baselines3.common.logger import configure as sb3_configure_logger
import gymnasium as gym


def write_info(experiment_path, info):
    with open(os.path.join(experiment_path, "info.yml"), "w") as f:
        f.write(yaml.dump(info))


def train_sb3():
    parser = ArgumentParser()
    parser.add_argument('--algo', default="SAC", type=str, help="name of the algorithm")
    parser.add_argument('--env', default="BipedalWalker-v3", type=str, help="name of the gym environment")
    parser.add_argument('--seed', default=0, type=int, help="manual seed")
    args = parser.parse_args()

    with open(os.path.join("config", f'{args.algo}.yml'), "r") as f:
        try:
            params = yaml.load(f, yaml.Loader)[args.env]
            total_timesteps = params.pop("n_timesteps")
            if params.get("policy_kwargs"):
                # sorry, ugly
                exec(f"params['policy_kwargs'] = {params['policy_kwargs']}")
        except KeyError:
            print(f"No hyperparameters for {args.env} found")
            params = {'policy': "CnnPolicy"}
            total_timesteps = 1_000_000

    print(f'Training {args.algo} with params {params}')

    set_random_seed(args.seed)

    env = gym.make(args.env)

    if args.algo == "SAC":
        model = SAC(env=env, **params)
    else:
        raise KeyError(f"Algorithm {args.algo} unknown")

    experiment_path = os.path.join("results", args.env, f"{args.algo}", f"s{args.seed}")

    if os.path.exists(experiment_path):
        shutil.rmtree(experiment_path)
        print(f"Warning: {experiment_path} already exists. Will be overwritten...")
    os.makedirs(experiment_path)

    eval_callback = EvalCallback(env, log_path=experiment_path, eval_freq=total_timesteps//100, deterministic=True,
                                 render=False, n_eval_episodes=3, warn=False, verbose=False)

    os.makedirs(experiment_path, exist_ok=True)

    write_info(experiment_path, {
            "algo": args.algo,
            "env": args.env,
            "seed": args.seed,
            "training_start_time": datetime.datetime.now()
    })

    new_logger = sb3_configure_logger(experiment_path, ["csv", "tensorboard"])
    model.set_logger(new_logger)

    model.learn(
        total_timesteps=total_timesteps,
        log_interval=total_timesteps//100,
        progress_bar=True,
        callback=[eval_callback]  # , state_trajectory_callback
    )

    model.save(os.path.join(experiment_path, "model.zip"))

    return model


if __name__ == '__main__':
    train_sb3()
