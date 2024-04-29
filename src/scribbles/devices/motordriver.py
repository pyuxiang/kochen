def execute_twice(f):
    def helper(*args, **kwargs):
        for i in range(2):
            result = f(*args, **kwargs)
        return result
    return helper

class MotorDriver:

    def __init__(self, path):
        self._com = serial.Serial(path, timeout=.1)

    def get_controller(self, channel: int, steps_per_revolution: int = 4800):
        return MotorController(self, channel, steps_per_revolution)

class MotorController:
    """ For each channel of DTRM40 """

    def __init__(self, driver, channel, steps_per_revolution):
        self.driver = driver
        channel = int(channel)
        assert channel in [0,1]
        self.channel = channel
        self.steps_per_revolution = steps_per_revolution

    def _write(self, *args):
        self.driver._com.write("{};".format(" ".join(map(str, args))).encode())

    def _read(self):
        return self.driver._com.readline().decode().strip()

    def _rwrite(self, *args):
        self._write(*args)
        return self._read()

    def deg2step(self, degree) -> int:
        return int(self.steps_per_revolution * (degree % 360)/360)

    def step2deg(self, step) -> float:
        return step * 360 / self.steps_per_revolution

    #######################################

    def initialize(self):
        self._write("setvolt", self.channel, 1.5)
        self._write("interpol", self.channel, 2)
        self._write("setspeed", self.channel, 170)
        self.set_zero()
        self.set_on()

    @execute_twice
    def set_on(self):
        self._write("on", self.channel)

    @execute_twice
    def set_off(self):
        self._write("off", self.channel)

    @execute_twice
    def set_zero(self):
        # Somehow needs four times...
        self._write("zero", self.channel)
        self._write("zero", self.channel)

    def get_position(self):
        """
        Multiple position calls needed, due to occasional readout errors,
        e.g. [..., 190, 193, 196, 0, 202, ...]. First readout clears
        remnant buffer, second and third does a position verification.
        """
        try:
            position1 = int(self._rwrite("POS?", self.channel))
            position2 = int(self._rwrite("POS?", self.channel))
            position3 = int(self._rwrite("POS?", self.channel))
            if position2 == position3:
                return position3
        except:
            pass
        return self.get_position() # restart if wrong command

    @execute_twice
    def get_position_degree(self):
        pos = self.get_position()
        # if pos is None: return None
        return self.step2deg(pos)

    @execute_twice
    def set_position(self, position):
        assert isinstance(position, int)
        self._write("go", self.channel, position)

    def set_position_blocking(self, position) -> None:
        """ Blocking """
        self.set_position(position)
        timeout = 10
        deadline = time.time_ns() + timeout * 1e9
        fail_count = 0
        while True:
            if self.get_position() == position:
                break
            if fail_count > 3:
                raise RuntimeException("Motor unwilling to move...")
            if time.time_ns() > deadline:
                deadline = time.time_ns() + timeout * 1e9
                self.set_position(position)
                fail_count += 1
                continue
            time.sleep(.1)

    @execute_twice
    def set_position_degree(self, degree):
        self.set_position(self.deg2step(degree))
