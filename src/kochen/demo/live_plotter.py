#!/usr/bin/env python3
# Justin, 2023-05-28
"""Plots live graph using handler.

Different ways of instantiating the main window of matplotlib, but
probably the easiest is to enable interactive mode using 'plt.ion()'[1].
Other solutions exist, but the main problem is getting the plots to behave
in another thread/process. Listing for completeness:

  * Blitting using 'FuncAnimation(fig, update, frames=gen(), init_func=init, blit=True)
  * Threading/MProcess and using 'window.after' in conjunction with 'plt.show()'.
    Inter-thread communication using queues.
      * Data queues is the usual
      * Callback queues also possible by decorating the plot/savefig/draw functions
        This may be relatively backend-dependent.

[1]: https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.isinteractive.html#matplotlib.pyplot.isinteractive

# FuncAnimation must be plotted in main thread, otherwise will fail
# with disconnection to DISPLAY, e.g. 'ValueError:
# set_wakeup_fd only works in main thread of the main interpreter'.
#
# i.e. the following does not work:
# Process(target=lambda: FuncAnimation(fig, ...); plt.show()).start()
# Thread(target=lambda: FuncAnimation...)
"""

import matplotlib.pyplot as plt

plt.ion()


class Grapher:
    def __init__(self):
        pass

    def start(self):
        pass

    # x = np.linspace(0, 6*np.pi, 100)
    # y = np.sin(x)
    # line1, = ax.plot(x, y, 'r-')
    # for phase in np.linspace(0, 10*np.pi, 500):
    #     line1.set_ydata(np.sin(x + phase))
    #     fig.canvas.draw()
    #     fig.canvas.flush_events()


"""
import threading
import queue
import functools
import matplotlib
import time

# matplotlib.use("tkagg")
# import matplotlib.pyplot as plt
def redirect(f):
    def helper(*args, **kwargs):
        global send, ret, pthread
        if threading.current_thread() == pthread:
            return f(*args, **kwargs)
        else:
            send.put(functools.partial(f, *args, **kwargs))
            return ret.get(True)  # blocking
    return helper
target_func = [
    (matplotlib.axes.Axes, "plot"),
    (matplotlib.figure.Figure, "savefig"),
    (matplotlib.backend_agg.FigureCanvasTkAgg, "draw"),
]
for fs in target_func:
    setattr(fs[0], fs[1], redirect(getattr(fs[0], fs[1])))

def update(window, send, ret):
    try:
        callback = ret.get(False)  # non-blocking
        retvalue = callback()
        ret.put(retvalue)
    except:
        None
    window.after(10, update, window, send, ret)

def animate():
    global pthread, send, ret
    pthread = threading.current_thread()
    send = queue.Queue()
    ret = queue.Queue()

    global ax, fig
    fig, ax = plt.subplots()
    window = plt.get_current_fig_manager().window
    window.after(10, update, window, send, ret)
    plt.show()

thread = threading.Thread(target=animate, daemon=True)
thread.start()

for i in range(10):
    ax.plot([1,i+1], [1,(i+1)**0.5])
    fig.canvas.draw()
    time.sleep(1)
"""
