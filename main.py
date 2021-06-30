import sys
from argparse import ArgumentParser
from time import sleep

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
        from torch import multiprocessing as mp
        from deep.policy import Policy
        from deep.optimizer import SharedAdam
        from deep.constants import CUDA0, LEARNING_RATE, SEED, NUM_PROCESSES

        torch.set_default_tensor_type('torch.FloatTensor')
        torch.manual_seed(SEED)
        mp.set_start_method("spawn")

        checkpoint = None
        if opt.checkpoint is not None:
            checkpoint = torch.load(opt.checkpoint)

        shared_model = Policy().to(CUDA0)
        if checkpoint is not None:
            shared_model.load_state_dict(checkpoint['model'])
        shared_model.share_memory()

        optimizer = SharedAdam(shared_model.parameters(), lr=LEARNING_RATE)
        if checkpoint is not None:
            optimizer.load_state_dict(checkpoint['optimizer'])
        optimizer.share_memory()

        try:
            processes = []

            counter = mp.Value('i', 0)
            lock = mp.Lock()

            p = mp.Process(target=deep.test, args=(NUM_PROCESSES, shared_model, counter))
            p.start()
            processes.append(p)

            for rank in range(0, NUM_PROCESSES):
                p = mp.Process(target=deep.train, args=(
                    rank,
                    shared_model,
                    counter,
                    lock,
                    optimizer,
                    CUDA0,
                ))
                p.start()
                processes.append(p)
            for p in processes:
                p.join()
        except KeyboardInterrupt as e:
            torch.save({
                "model": shared_model.state_dict(),
                "optimizer": optimizer.state_dict(),
            }, "keyboard_interrupt.checkpoint")
            sleep(5)
            raise e

        torch.save({
            "model": shared_model.state_dict(),
            "optimizer": optimizer.state_dict(),
        }, "training_end.checkpoint")

if __name__ == "__main__":
    main()
