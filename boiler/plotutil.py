def import_mpl_presentation():
    """Prepares matplotlib params for presentations.

    Text size is made larger without squeezing the graph.
    """
    import matplotlib
    matplotlib.rcParams["toolbar"] = "None"  # hide interactive toolbar

    # Do the above before importing 'plt', which inherits parameters
    import matplotlib.pyplot as plt
    plt.rcParams.update({'axes.titlesize': 'x-large',
                        'axes.labelsize': 'x-large'})