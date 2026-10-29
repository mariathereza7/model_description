"""Small dependency-free PID controller used by the pose node."""


class PID:
    """Discrete PID with output limits and conditional anti-windup."""

    def __init__(self, kp, ki, kd, output_min=None, output_max=None):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.output_min = output_min
        self.output_max = output_max
        self.integral = 0.0
        self.previous_error = None

    def reset(self):
        self.integral = 0.0
        self.previous_error = None

    def update(self, error, dt):
        dt = max(float(dt), 1e-6)
        derivative = 0.0 if self.previous_error is None else (error - self.previous_error) / dt
        candidate_integral = self.integral + error * dt
        raw = self.kp * error + self.ki * candidate_integral + self.kd * derivative
        saturated = raw
        if self.output_min is not None:
            saturated = max(self.output_min, saturated)
        if self.output_max is not None:
            saturated = min(self.output_max, saturated)
        # Integrate only when saturation is not being worsened by the error.
        if saturated == raw or (saturated == self.output_max and error < 0) or (
                saturated == self.output_min and error > 0):
            self.integral = candidate_integral
        self.previous_error = error
        return saturated
