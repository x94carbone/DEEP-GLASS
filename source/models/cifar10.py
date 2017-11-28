from models.generic_models import conv22tanh,conv22relu,loadNet,convAlexrelu,AlexNet


def bruna(pretrained_path=False, **kwargs):
    """Constructs a very simple convNet
    Args:
        pretrained_path (bool): If True, returns the pretrained model on the path
    """
    
    model = bruna(layers=[3*1024,500,10])
    if pretrained_path:
        return loadNet(pretrained_path,model)
    return model



def convTest(pretrained_path=False, **kwargs):
    """Constructs a very simple convNet
    Args:
        pretrained_path (bool): If True, returns the pretrained model on the path
    """
    model = conv22relu(layers=[3, 2, 4, 32,10],im_dim=32)
    if pretrained_path:
        return loadNet(pretrained_path,model)
    return model

def conv1020relu(pretrained_path=False, **kwargs):
    """todo
    Args:
        pretrained_path (bool): If True, returns the  pretrained model on the path
    """
    model = conv22relu(layers=[3, 10, 20, 100,10],im_dim=32)
    if pretrained_path:
        return loadNet(pretrained_path,model)
    return model

def conv6464relu(pretrained_path=False, **kwargs):
    """alex like convnet
    Args:
        pretrained_path (bool): If True, returns the  pretrained model on the path
    """
    model = convAlexrelu(layers=[3,64,64,192,10], k_dims=[5,5],im_dim = 32)
    if pretrained_path:
        return loadNet(pretrained_path,model)
    return model

def alex6464(pretrained_path=False, **kwargs):
    """alex like convnet
    Args:
        pretrained_path (bool): If True, returns the  pretrained model on the path
    """
    model = AlexNet()
    if pretrained_path:
        return loadNet(pretrained_path,model)
    return model

def alex6464raw(pretrained_path=False, **kwargs):
    """alex like convnet
    Args:
        pretrained_path (bool): If True, returns the  pretrained model on the path
    """
    model = AlexNet(raw=True)
    if pretrained_path:
        return loadNet(pretrained_path,model)
    return model

def conv1020tanh(pretrained_path=False, **kwargs):
    """Constructs a very simple convNet
    Args:
        pretrained_path (bool): If True, returns the  pretrained model on the path
    """
    model = conv22tanh(layers=[3, 10, 20, 100,10],im_dim=32)
    if pretrained_path:
        return loadNet(pretrained_path,model)
    return model

