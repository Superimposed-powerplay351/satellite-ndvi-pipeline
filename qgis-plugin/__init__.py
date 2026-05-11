def classFactory(iface):
    from .ndvi_loader import NdviPipelineLoader
    return NdviPipelineLoader(iface)
