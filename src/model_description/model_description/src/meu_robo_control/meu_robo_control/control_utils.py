import math

def wrap_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))

def yaw_from_quaternion(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))
