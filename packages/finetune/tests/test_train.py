from finetune.train import build_lora_command


def test_command_has_required_flags():
    cmd = build_lora_command(model="m", data_dir="data/ft",
                             adapter_dir="data/adapters/qlora",
                             iters=200, batch_size=1, num_layers=8,
                             learning_rate=1e-5)
    assert cmd[:4] == ["python", "-m", "mlx_lm.lora", "--model"]
    assert "--train" in cmd
    assert cmd[cmd.index("--data") + 1] == "data/ft"
    assert cmd[cmd.index("--adapter-path") + 1] == "data/adapters/qlora"
    assert cmd[cmd.index("--iters") + 1] == "200"
    assert cmd[cmd.index("--num-layers") + 1] == "8"
    assert cmd[cmd.index("--batch-size") + 1] == "1"
    assert cmd[cmd.index("--learning-rate") + 1] == "1e-05"


def test_defaults():
    cmd = build_lora_command(model="m", data_dir="d", adapter_dir="a")
    assert "--iters" in cmd and "--adapter-path" in cmd
