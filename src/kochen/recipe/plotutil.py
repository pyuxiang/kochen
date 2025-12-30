# Do not import this module unless explicitly specified.
# Mainly a book of recipes.
# References:
#   [1]: https://matplotlib.org/stable/users/explain/event_handling.html#event-connections


def import_mpl_presentation():
    """Prepares matplotlib params for presentations.

    Text size is made larger without squeezing the graph.
    """
    import matplotlib

    matplotlib.rcParams["toolbar"] = "None"  # hide interactive toolbar

    # Do the above before importing 'plt', which inherits parameters
    import matplotlib.pyplot as plt

    plt.rcParams.update({"axes.titlesize": "x-large", "axes.labelsize": "x-large"})


def create_parasitic_axes():
    """Creates a secondary axis for overlaying correlated plots.

    This method is most efficient, compared to the multitude of outdated
    syntax in the official documentation examples.
    """
    import matplotlib.pyplot as plt

    # Example data
    xs = [0, 1, 2, 3, 4]
    ys = [1, 2, 3, 1, 5]
    zs = [0.01, 0.02, 0.01, -0.12, 0.03]

    # Regular plotting as per usual
    fig, ax = plt.subplots(figsize=(10, 5))
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


def set_45degree_datetimes():
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    fig, ax = plt.subplots()
    dformat = mdates.DateFormatter("%-d %b, %-I%P")  # e.g. "7 Jun, 4am"
    ax.xaxis.set_major_formatter(dformat)
    plt.xticks(rotation=45, ha="right", rotation_mode="anchor")


def plot_3d(
    data,
    xlabel,
    ylabel,
    zlabel,
    mask=None,
    reverse_x=False,
    reverse_y=False,
    title="",
    **kwargs,
):
    import re
    import matplotlib.pyplot as plt
    import numpy as np

    """

    Examples:

        # Input methods
        >>> plot_3d([xs, ys, zs], ...)
        >>> plot_3d([(x0, y0, z0), ...], ...)
        >>> plot_3d({"{{xlabel}}": xs, ...}, ...)

        # Passing plotting parameters
        >>> plot_3d(..., _xlabel="Quantity", _xscale="log")

    TODO:
        Abstract away the internals to return the xrow, yrow and zrow
        data directly to avoid excessive customization of pcolormesh
        in the function signature.
    """

    # Allow data to be flat arrays as well
    if not isinstance(data, dict):
        try:
            data = np.array(data)
            if data.shape[-1] == 3:
                data = data.T
            labels = [xlabel, ylabel, zlabel, *[f"p{i}" for i in range(data.shape[0])]]
            data = dict(zip(labels, data))
        except:
            raise ValueError("Unsupported data format.")

    # Enable value bypass for kwargs using '_' prepended, to avoid conflict with existing kwargs
    kwargs = dict([(k.lstrip("_"), v) for k, v in kwargs.items()])
    # TODO(Justin): Add multiple filters
    xs = np.array(data[xlabel])
    ys = np.array(data[ylabel])
    zs = np.array(data[zlabel])
    if mask is not None:
        xs = xs[mask]
        ys = ys[mask]
        zs = zs[mask]

    # Extract axes and convert to map for efficiency
    # xs_unique = sorted(set(xs))  # masked
    # ys_unique = sorted(set(ys))
    xs_unique = sorted(set(data[xlabel]))  # unmasked
    ys_unique = sorted(set(data[ylabel]))
    xs_mapper = dict([(x, i) for i, x in enumerate(xs_unique)])
    ys_mapper = dict([(y, i) for i, y in enumerate(ys_unique)])

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
    if mask is None:
        data_argmax = dict([(k, np.array(v)[z_argmax]) for k, v in data.items()])
    else:
        data_argmax = dict([(k, np.array(v)[mask][z_argmax]) for k, v in data.items()])
    x_max = data_argmax[xlabel]
    y_max = data_argmax[ylabel]
    z_max = data_argmax[zlabel]

    # Plot stuff
    _title = str(data_argmax)
    # _title = f"HVOLT {round(max_hvolt,1)}V, TVOLT {round(max_threshvolt)}mV, Pairs {pair}cps, Raw singles {singles}cps"
    if title:
        _title = f"{title}\n{_title}"

    fig, ax = plt.subplots(1, 1, figsize=(8, 6))
    plt.suptitle(_title)
    # plt.pcolormesh(xs_unique, ys_unique, zs_grid, cmap=plt.cm.jet, shading="nearest", vmin=0)
    plt.pcolormesh(xs_unique, ys_unique, zs_grid, cmap=plt.cm.jet, shading="nearest")
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
    plt.savefig(re.sub(r"\s", "_", title) + ".png")
    return


def assign_dynamic_timescale(ax):
    """Modifies hourly time axis into a dynamic timescale with varying offsets."""
    import matplotlib.ticker as mticker
    import numpy as np

    # Cache axis limits to signal redraw event
    lims = [None, None]
    fig = ax.get_figure()
    autoloc = mticker.MaxNLocator(nbins=10, steps=[1, 2, 2.5, 5, 10])

    def rescale(event):
        # Stop after a redraw event
        xlims = ax.get_xlim()
        ylims = ax.get_ylim()
        if lims[0] == xlims and lims[1] == ylims:
            return
        lims[0] = xlims
        lims[1] = ylims

        # Determine required xticklabels and xlabels using xlim
        spacing = (xlims[1] - xlims[0]) * 3600 / 6
        factor = 1  # scaling factor
        if spacing > 1200:  # 20 minutes
            label = "hours"
            factor = 3600
        elif spacing > 20:  # 20 seconds -> minutes
            label = "mins"
            factor = 60
        elif spacing > 0.1:  # 100 ms -> seconds
            label = "s"
            factor = 1
        else:  # 100 us -> milliseconds
            label = "ms"
            factor = 1e-3

        # Prescale xticks and set location of ticks
        scaled_xlims = (xlims[0] * 3600 / factor, xlims[1] * 3600 / factor)
        xticks = autoloc.tick_values(*scaled_xlims)
        fixedloc = mticker.FixedLocator(xticks * factor / 3600)
        ax.xaxis.set_major_locator(fixedloc)

        # Trickle down units to calculate time offset
        minabs_xtick = np.min(np.abs(xticks))
        remainder = minabs_xtick
        _hours = _mins = _secs = 0
        if label == "ms":
            _secs = int(remainder // 1000)
            remainder -= _secs * 1000
            _mins = int(_secs // 60)
            _secs -= _mins * 60
            _hours = int(_mins // 60)
            _mins -= _hours * 60
        elif label == "s":
            _mins = int(remainder // 60)
            remainder -= _mins * 60
            _hours = int(_mins // 60)
            _mins -= _hours * 60
        elif label == "mins":
            _hours = int(remainder // 60)
            remainder -= _hours * 60

        # Construct time offset string
        xlabel = f"Elapsed time ({label})"
        timeoffset_str = ""
        if _hours:
            timeoffset_str += f"{_hours}h "
        if _mins:
            timeoffset_str += f"{_mins}m "
        if _secs:
            timeoffset_str += f"{_secs}s "
        if timeoffset_str:
            xlabel = f"{xlabel} + {timeoffset_str[:-1]}"
        ax.set_xlabel(xlabel)

        # Set xlabels and xticklabels
        xticks -= minabs_xtick - remainder  # apply offset
        xticklabels = np.round(xticks, 6)  # clean rounding errors
        if all([v.is_integer() for v in xticklabels]):
            xticklabels = np.int32(xticklabels)  # clean integers
        xticklabels = list(map(str, xticklabels))
        ax.set_xticklabels(xticklabels)

        # Force a redraw event to draw in new axis labels
        fig.draw(event.renderer)

    fig.canvas.mpl_connect("draw_event", rescale)
    return rescale  # hold reference to avoid GC, see [1]


def generate_fit_label(label, plabels):
    """Provides a consistent legend for fitted parameters.

    Args:
        label: Label for plot.
        plabels: Output from 'mathutil.fit'.

    Examples:
        >>> from kochen.mathutil import fit
        >>> popt, plabels = fit(f, xs, ys, labels=True)
        >>> # plabels = ['A = 3.77+/-0.05', 'μ = 7.14+/-0.04', 'σ = 0.880+/-0.030']
        >>> label = generate_fit_label("Signal curve", plabels)
        >>> print(label)
        Signal curve
           |  A = 3.76+/-0.05
           |  μ = 7.14+/-0.04
           |  σ = 0.881+/-0.030
        >>> plt.plot(xs, ys, label=label)
    """
    return f"{label}\n" + "\n".join([f"   |  {p}" for p in plabels])


def recipe_generic_plotting():
    """Lists the most common features of matplotib used thus far.

    Basically as a self-reference for stylistic hints, etc.
    """
    xs = ys = [1, 2]

    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(
        2, 1, figsize=(6, 4), dpi=100, sharex=True, height_ratios=[1.5, 1]
    )

    # Generic plot
    plt.sca(axs[0])
    plt.plot(xs, ys, ".", markersize=3, alpha=0.5, label="label1")
    plt.plot(xs, ys, linewidth=1, label="label2")
    plt.ylim(1, 2)
    plt.xlim(2, 3)
    plt.ylabel("y axis")
    plt.xlabel("x axis")
    plt.yscale("log")
    plt.title("top graph")
    plt.legend()

    # Parasitic axis
    plt.sca(axs[1])
    pax = axs[1].twinx()
    # See above

    # Overall plot information
    plt.suptitle("Big title", fontsize=12)
    plt.tight_layout()
    fig.savefig("savefile.png")
    plt.show()


def format_xdates(ax, angle=45, format="%-d %b, %-I%P", dx=0, dy=0):
    # https://stackoverflow.com/a/67459618
    import matplotlib.dates as mdates
    from matplotlib.transforms import ScaledTranslation

    ax_cache = plt.gca()
    fig = ax.get_figure()
    plt.sca(ax)

    dformat = mdates.DateFormatter(format)  # e.g. "7 Jun, 4am"
    ax.xaxis.set_major_formatter(dformat)
    plt.xticks(rotation=angle, ha="right", rotation_mode="anchor")

    offset = ScaledTranslation(dx / fig.dpi, dy / fig.dpi, fig.dpi_scale_trans)
    # apply offset to all xticklabels
    for label in ax.xaxis.get_majorticklabels():
        label.set_transform(label.get_transform() + offset)

    # Clear ax cache
    plt.sca(ax_cache)


def get_cwheel(scheme: str = "bright", order=None):
    from tol_colors import tol_cset

    cmap = tol_cset(scheme)
    i = 0
    while True:
        if order is None:
            yield cmap[i]
        else:
            yield cmap[order[i]]
        i += 1


cwheel = get_cwheel()

from matplotlib.colors import colorConverter as cc


def parse_color_as_rgb(color):
    """Convert to RGB, each in float [0,1] range."""
    if isinstance(color, str):
        if color.startswith("#"):  # hex color
            r = int(color[1:3], base=16) / 255
            g = int(color[3:5], base=16) / 255
            b = int(color[5:7], base=16) / 255
        else:  # named color
            r, g, b = cc.to_rgb(color)
    else:
        r, g, b, *_ = color  # float values
        if r > 1 or g > 1 or b > 1:  # raw values
            r /= 255
            g /= 255
            b /= 255
    return r, g, b


def lighten(color, alpha: float = 1, bg_color="white"):
    """Convert RGBA into solid RGB.

    Problem with PostScript backend is that transparency is not supported.
    A workaround is to convert the alpha-based color into a solid RGB color,
    by blending with the background using 'alpha' as a parameter.

    Reference:
        [1]: https://stackoverflow.com/a/2645218
    """
    color = parse_color_as_rgb(color)
    bg_color = parse_color_as_rgb(bg_color)
    result = [(1 - alpha) * bv + alpha * v for v, bv in zip(color, bg_color)]
    return result


def color_axis(ax, color, right=False):
    ax.spines["right" if right else "left"].set_color(color)
    ax.yaxis.label.set_color(color)
    ax.tick_params(axis="y", colors=color)


# Annotations
def add_annotations():
    def hover(event):
        vis = annot.get_visible()
        if event.inaxes == ax:
            cont, ind = sc.contains(event)
            if cont:
                update_annot(ind)
                annot.set_visible(True)
                fig.canvas.draw_idle()
            else:
                if vis:
                    annot.set_visible(False)
                    fig.canvas.draw_idle()

    fig, ax = plt.subplots()
    sc = plt.scatter(v, e, c=np.arange(len(e)), cmap=plt.get_cmap("viridis"))
    annot = ax.annotate(
        "",
        xy=(0, 0),
        xytext=(20, 20),
        textcoords="offset points",
        bbox=dict(boxstyle="round", fc="w"),
        arrowprops=dict(arrowstyle="->"),
    )
    annot.set_visible(False)

    def update_annot(ind):
        idx = ind["ind"]
        pos = sc.get_offsets()[ind["ind"][0]]
        annot.xy = pos
        annot.set_text(
            ", ".join(
                list(
                    map(
                        str,
                        [
                            temp[idx],
                            hvolt[idx],
                            tvolt[idx],
                        ],
                    )
                )
            )
        )
        annot.get_bbox_patch().set_alpha(0.4)

    fig.canvas.mpl_connect("motion_notify_event", hover)
    plt.show()
