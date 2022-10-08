# Do not import this module unless explicitly specified.
# Mainly a book of recipes.

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

def create_parasitic_axes():
    """Creates a secondary axis for overlaying correlated plots.

    This method is most efficient, compared to the multitude of outdated
    syntax in the official documentation examples.
    """
    import matplotlib.pyplot as plt

    # Example data
    xs = [0,1,2,3,4]
    ys = [1,2,3,1,5]
    zs = [0.01, 0.02, 0.01, -0.12, 0.03]

    # Regular plotting as per usual
    fig, ax = plt.subplots(figsize=(10,5))
    plt.plot(xs, ys, label="$V_{in}$")
    plt.xlabel("Time (ms)")
    plt.ylabel("Voltage (V)")
    plt.legend()

    # Starts here: Create another axis sharing x-axis
    ax2 = ax.twinx()
    plt.sca(ax2)  # easiest to set as current axis to continue 'plt' syntax
    plt.plot(xs, zs, c="tab:green", label="$I_{out}$")
    plt.ylabel("Current (A)")
    plt.legend()

    plt.tight_layout()
    plt.show()