---
order: 1
---

### 🌍 [Appworld Experiment](appworld/quickstart.md)

We tested ReMe on Appworld using qwen3-8b:

| Method       | pass@1            | pass@2            | pass@4            |
|--------------|-------------------|-------------------|-------------------|
| without ReMe | 0.083             | 0.140             | 0.228             |
| with ReMe    | 0.109 **(+2.6%)** | 0.175 **(+3.5%)** | 0.281 **(+5.3%)** |

Pass@K measures the probability that at least one of the K generated samples successfully completes the task (
score=1).  
The current experiment uses an internal AppWorld environment, which may have slight differences.

You can find more details on reproducing the experiment in [quickstart.md](appworld/quickstart.md).

### 🧊 [Frozenlake Experiment](frozenlake/quickstart.md)

|                                        without ReMe                                        |                                         with ReMe                                          |
|:------------------------------------------------------------------------------------------:|:------------------------------------------------------------------------------------------:|
| <p align="center"><img src="../figure/frozenlake_failure.gif" alt="GIF 1" width="30%"></p> | <p align="center"><img src="../figure/frozenlake_success.gif" alt="GIF 2" width="30%"></p> |

We tested on 100 random frozenlake maps using qwen3-8b:

| Method       | pass rate        |
|--------------|------------------|
| without ReMe | 0.66             |
| with ReMe    | 0.72 **(+6.0%)** |

You can find more details on reproducing the experiment in [quickstart.md](frozenlake/quickstart.md).

### 🔧 [BFCL-V3 Experiment](bfcl/quickstart.md)

We tested ReMe on BFCL-V3 multi-turn-base (randomly split 50train/150val) using qwen3-8b:

| Method       | pass@1              | pass@2              | pass@4              |
|--------------|---------------------|---------------------|---------------------|
| without ReMe | 0.2472              | 0.2733              | 0.2922              |
| with ReMe    | 0.3061 **(+5.89%)** | 0.3500 **(+7.67%)** | 0.3888 **(+9.66%)** |
