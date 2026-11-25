"""Fine-tune the text classifier head on data/train_v3.jsonl (needs torch and a CUDA GPU)."""
import argparse
import json

import torch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=2e-4)
    args = ap.parse_args()
    torch.manual_seed(args.seed)
    device = torch.device("cuda")
    with open(args.data, encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh]
    features = torch.tensor([r["features"] for r in rows], device=device)
    labels = torch.tensor([r["label"] for r in rows], device=device)
    model = torch.nn.Linear(features.shape[1], 2).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    for _ in range(args.epochs):
        opt.zero_grad()
        loss = torch.nn.functional.cross_entropy(model(features), labels)
        loss.backward()
        opt.step()
    print(f"eval loss {loss.item():.3f}")


if __name__ == "__main__":
    main()
