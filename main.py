import sys
from argparse import ArgumentParser

PY_VER = 3.8


def main() -> None:
    if sys.version_info[0] < 3:
        raise EnvironmentError(f"You must use Python 3 or higher. Development is currently ongoing on Python {PY_VER}.")

    parser = ArgumentParser()
    parser.add_argument("--mode", default="play", choices=["train", "evaluate", "play"])
    parser.add_argument("--checkpoint", default=None, help="path to checkpoint to restore")
    parser.add_argument("--device_ids", default="0", type=lambda x: list(map(int, x.split(','))),
                        help="Names of the devices comma separated.")

    opt = parser.parse_args()

    if opt.mode == "play":
        import play
        try:
            play.run()
        except (KeyboardInterrupt, Exception) as e:
            play.stop()
            raise e

    if opt.mode == "train":
        import deep
        import torch
        from deep.policy import Policy
        from deep.constants import CUDA0, CUDA1, LEARNING_RATE

        torch.set_default_tensor_type('torch.FloatTensor')
        torch.manual_seed(1625582114)

        deep.train(checkpoint=opt.checkpoint, device=CUDA0)


if __name__ == "__main__":
    main()
