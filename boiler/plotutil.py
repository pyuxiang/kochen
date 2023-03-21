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
    ax2.yaxis.label.set_color("tab:green")
    ax2.tick_params(axis="y", colors="tab:green")

    plt.ylabel("Current (A)")
    plt.legend()

    plt.tight_layout()
    plt.show()

def plot_3d(data, xlabel, ylabel, zlabel, mask, reverse_x=False, reverse_y=False, title="", **kwargs):
    """
    
    TODO:
        Abstract away the internals to return the xrow, yrow and zrow
        data directly to avoid excessive customization of pcolormesh
        in the function signature.
    """

    # Enable value bypass for kwargs using '_' prepended
    kwargs = dict([(k.lstrip("_"),v) for k,v in kwargs.items()])
    # TODO(Justin): Add multiple filters
    xs = data[xlabel][mask]
    ys = data[ylabel][mask]
    zs = data[zlabel][mask]

    # Extract axes and convert to map for efficiency
    # xs_unique = sorted(set(xs))  # masked
    # ys_unique = sorted(set(ys))
    xs_unique = sorted(set(data[xlabel]))  # unmasked
    ys_unique = sorted(set(data[ylabel]))
    xs_mapper = dict([(x,i) for i,x in enumerate(xs_unique)])
    ys_mapper = dict([(y,i) for i,y in enumerate(ys_unique)])

    # Generate 2D plot
    # We do this so missing values can be excluded
    zs_grid = np.ones([len(ys_unique), len(xs_unique)], dtype=np.float64) * np.nan
    for x, y, z in zip(xs, ys, zs):
        xidx = xs_mapper.get(x, None)
        yidx = ys_mapper.get(y, None)
        
        # TODO: Remove this check - all x and y values should exist
        if xidx is None or yidx is None:
            continue
        zs_grid[yidx][xidx] = z
    
    # TODO(Justin): See if can do something with this too...
    z_argmax = np.argmax(zs)
    data_argmax = dict([(k,v[mask][z_argmax]) for k,v in data.items()])
    x_max = data_argmax[xlabel]
    y_max = data_argmax[ylabel]
    z_max = data_argmax[zlabel]
    
    # Plot stuff
    _title = str(data_argmax)
    #_title = f"HVOLT {round(max_hvolt,1)}V, TVOLT {round(max_threshvolt)}mV, Pairs {pair}cps, Raw singles {singles}cps"
    if title:
        _title = f"{title}\n{_title}"

    fig, ax = plt.subplots(1, 1, figsize=(8,6))
    plt.suptitle(_title)
    plt.pcolormesh(xs_unique, ys_unique, zs_grid, cmap=plt.cm.jet, shading="nearest", vmin=0)
    # Apply hatch pattern to missing values: https://stackoverflow.com/a/35905483
    ax.patch.set(hatch="x", edgecolor="black")
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    for k, v in kwargs.items():
        getattr(plt, k.lstrip("_"))(v)
    if reverse_x:
        plt.gca().invert_xaxis()
    if reverse_y:
        plt.gca().invert_yaxis()
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(re.sub(r"\s", "_", title)+".png")
    return