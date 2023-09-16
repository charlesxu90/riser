from torch import nn
# from torchinfo import summary

# from utilities import get_config


class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1):
        super().__init__()

        # Parameters
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.stride = stride
        self.activation = nn.ReLU(inplace=True)

        # Convolutional blocks
        self.blocks = nn.Identity()

        # Match dimensions of block's input and output for summation
        self.shortcut = nn.Sequential(
            nn.Conv1d(in_channels, out_channels, 1, stride=stride, bias=False),
            nn.BatchNorm1d(out_channels)
        )

    def conv_block(self, in_channels, out_channels, kernel_size, last=False, **kwargs):
        layers = [
            nn.Conv1d(in_channels, out_channels, kernel_size, **kwargs),
            nn.BatchNorm1d(out_channels),
        ]

        # Activate all but the last hidden layer so that the block
        # output and residual can be summed
        if last == False:
            layers.append(nn.ReLU(inplace=True))
        
        return nn.Sequential(*layers)

    def forward(self, x):
        residual = self.shortcut(x) if self.should_apply_shortcut else x
        out = self.blocks(x)
        out = self.activation(out + residual)
        return out

    @property
    def should_apply_shortcut(self):
        return self.in_channels != self.out_channels or self.stride != 1


class BasicBlock(ResidualBlock):
    def __init__(self, in_channels, out_channels, stride=1):
        super().__init__(in_channels, out_channels, stride)

        self.blocks = nn.Sequential(
            self.conv_block(in_channels, out_channels, 3, stride=stride, padding=1, bias=False),
            self.conv_block(out_channels, out_channels, 3, last=True, padding=1, bias=False)
        )


class BottleneckBlock(ResidualBlock):
    def __init__(self, in_channels, out_channels, reduction=4, stride=1):
        super().__init__(in_channels, out_channels, stride)

        self.channels = out_channels // reduction

        self.blocks = nn.Sequential(
            self.conv_block(in_channels, self.channels, 1, bias=False),
            self.conv_block(self.channels, self.channels, 3, stride=stride, padding=1, bias=False), # Downsample here as per line 107 https://github.com/pytorch/vision/blob/main/torchvision/models/resnet.py
            self.conv_block(self.channels, out_channels, 1, last=True, bias=False)
        )


class ResNet(nn.Module):
    def __init__(self, c):
        super(ResNet, self).__init__()
        self.in_channels = c.channels[0]

        # Feature extractor layer
        self.conv_block = nn.Sequential(
            nn.Conv1d(1, self.in_channels, c.kernel, padding=c.padding, stride=c.stride),
            nn.BatchNorm1d(self.in_channels),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2, stride=2, padding=1)
        )

        # Residual layers
        block = BottleneckBlock if c.block == 'bottleneck' else BasicBlock
        layers = []
        for i in range(c.n_layers):
            stride = 1 if i == 0 else 2
            layers.append(self._make_layer(block, c.channels[i], c.blocks[i], stride))
        self.layers = nn.ModuleList(layers)

        # Classifier
        self.decoder = nn.Sequential(
            nn.AdaptiveAvgPool1d(1), # Converts each channel into a single value
            nn.Flatten(1), # Concatenates channels
            nn.Linear(c.channels[-1], c.n_classes)
        )

        # Initialise weights and biases
        self._init_weights()

    def forward(self, x):
        x = x.unsqueeze(1)
        x = self.conv_block(x)
        for layer in self.layers:
            x = layer(x)
        x = self.decoder(x)
        return x

    def _make_layer(self, block, out_channels, n_blocks, stride):
        # First residual block in layer may downsample
        blocks = [block(self.in_channels, out_channels, stride=stride)]

        # In channels for next layer will be this layer's out channels
        self.in_channels = out_channels

        # Remaining residual blocks in layer
        for _ in range(1, n_blocks):
            blocks.append(block(self.in_channels, out_channels))

        return nn.Sequential(*blocks)
    
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv1d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, (nn.BatchNorm1d)):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
