from torch import nn
from torchinfo import summary

from utilities import get_config


class ConvRecNet(nn.Module):
    def __init__(self, c):
        super().__init__()

        # Convolutional layers
        conv_layers = []
        for i in range(c.n_conv_layers):
            # First layer takes 1D time-series input while the rest
            # take channel outputs from previous layer
            in_channels = 1 if i == 0 else c.layer_channels[i-1]
            conv_layers.append(self._make_layer(in_channels, c.layer_channels[i], c.layer_kernels[i]))
        self.conv_layers = nn.ModuleList(conv_layers)

        # Recurrent layers
        rec_layers = []
        for i in range(c.n_rec_layers):
            # First LSTM layer takes last conv layer output
            if i == 0:
                input_dim = c.conv_layer_channels[-1]
            # Subsequent layers take hidden output from previous layer
            else:
                input_dim = c.rec_hidden_size
            rec_layers.append(nn.LSTM(input_size=input_dim,
                                      hidden_size=c.rec_hidden_size,
                                      num_layers=c.n_rec_layers,
                                      batch_first=True,
                                      dropout=c.rec_dropout,
                                      bidirectional=c.rec_bidirectional))
        self.rec_layers = nn.ModuleList(rec_layers)

        # Classifier
        self.linear = nn.Linear(c.rec_hidden_size, c.n_classes)


    def forward(self, x):
        print(f"Raw x: {x.shape}")
        x = x.unsqueeze(1) # Add dimension to represent 1D input
        print(f"After unsqueeze x: {x.shape}")
        for layer in self.conv_layers:
            x = layer(x)
            print(f"After conv layer x: {x.shape}")

        # CNN output is (B,C,L) but LSTM input needs to be (B,L,C)
        # B = batch_size, C = features (channels), L = seq_length
        x = x.permute(0, 2, 1)
        print(f"After permute x: {x.shape}")

        for layer in self.rec_layers:
            x, (hn, cn) = layer(x)
            # x: (B,L,H) - H hidden states for every timestep in L
            # hn: (1,B,H) - H hidden states for the last timestep in L
            print(f"After LSTM layer x: {x.shape}")
            print(f"After LSTM layer hn: {hn.shape}")
            print(f"After LSTM layer cn: {cn.shape}")

        # TODO: Do we need a ReLU after LSTM?
        # TODO: Bidirectional implementation

        x = self.linear(x[:, -1, :]) # Get the hidden states for the last timestep in L. Equivalent to self.linear(hn) if # layers = 1

        # NB: Softmax not needed since it is incorporated into
        # torch implementation of CrossEntropyLoss. Can send the raw
        # logits there.

        return x

    def _make_layer(self, in_channels, out_channels, kernel_size, last=False):
        layers = [
            nn.Conv1d(in_channels, out_channels, kernel_size),
            nn.MaxPool1d(kernel_size=2, stride=2)
        ]

        # Activate all but the last hidden layer
        if last == False:
            layers.append(nn.ReLU(inplace=True))
        
        return nn.Sequential(*layers)


def main():
    config = get_config('config.yaml')
    model = ConvRecNet(config.cnn_rnn)
    summary(model, input_size=(64, 9036))


if __name__ == "__main__":
    main()