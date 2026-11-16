class PID:
    """PID discreto com anti-windup simples."""
    def __init__(self, kp, ki, kd, integral_limit=1.0e6):
        self.kp, self.ki, self.kd = float(kp), float(ki), float(kd)
        self.integral_limit = abs(float(integral_limit)); self.reset()

    def reset(self):
        self.integral = 0.0; self.previous_error = None

    def update(self, error, dt):
        if dt <= 0.0: return self.kp * error
        self.integral = max(-self.integral_limit, min(self.integral + error * dt, self.integral_limit))
        derivative = 0.0 if self.previous_error is None else (error - self.previous_error) / dt
        self.previous_error = error
        return self.kp * error + self.ki * self.integral + self.kd * derivative
