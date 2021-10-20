import torch
from torch import nn
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from torchinfo import summary

from resnet import ResNet, BottleneckBlock
from data import SignalDataset


def test(dataloader, model, device):
    n_samples = len(dataloader.dataset)
    model.eval()
    n_correct = 0
    with torch.no_grad():
        for X, y in dataloader:

            # Move batch to GPU
            X, y = X.to(device), y.to(device)
            
            # Compute prediction error
            pred = model(X)
            n_correct += (pred.argmax(1) == y).type(torch.float).sum().item()
    
    # Compute accuracy
    acc = n_correct / n_samples * 100
    return acc


def main():

    # TODO: CL args
    checkpt = "best-model.pth"

    # Create test dataloader

    # print("Creating datasets...")
    # checkpt_dir = "/g/data/xc17/Eyras/alex/working/rna-classifier/experiments/train-1"
    # data_dir = "/g/data/xc17/Eyras/alex/working/rna-classifier/5_MakeDataset"
    # test_cfile = f"{data_dir}/val_coding.pt"
    # test_nfile = f"{data_dir}/val_noncoding.pt"
    # batch_size = 1000

    checkpt_dir = "/home/alex/Documents/rnaclassifier/saved_models"
    data_dir = '/home/alex/Documents/rnaclassifier/local_data'
    test_cfile = f"{data_dir}/test_coding.pt"
    test_nfile = f"{data_dir}/test_noncoding.pt"
    batch_size = 64

    test_data = SignalDataset(test_cfile, test_nfile)
    test_loader = DataLoader(test_data, batch_size=batch_size, shuffle=False)

    # Get device for training

    device = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device)
    print(f"Using {device} device")

    # Define model

    model = ResNet(BottleneckBlock, [2,2,2,2]).to(device)
    model.load_state_dict(torch.load(f"{checkpt_dir}/{checkpt}"))
    summary(model)

    # Test

    acc = test(test_loader, model, device)
    print(f"Test accuracy: {acc:>0.1f}%")




if __name__ == "__main__":
    main()
 