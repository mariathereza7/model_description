"""Pose controller using rotate-translate-rotate maneuvers."""

import math

import rclpy
from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node


def wrap_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


class ManeuverPoseNode(Node):
    """Execute one pose goal as rotation, translation, then rotation."""

    def __init__(self):
        super().__init__('maneuver_pose_node')
        for name, default in (
                ('kp_rotate', 2.0), ('kp_translate', 1.0),
                ('position_tolerance', 0.05), ('yaw_tolerance', 0.05),
                ('max_linear_speed', 0.4), ('max_angular_speed', 1.5)):
            self.declare_parameter(name, default)
        self.kp_rotate = self.get_parameter('kp_rotate').value
        self.kp_translate = self.get_parameter('kp_translate').value
        self.position_tolerance = self.get_parameter('position_tolerance').value
        self.yaw_tolerance = self.get_parameter('yaw_tolerance').value
        self.max_linear_speed = self.get_parameter('max_linear_speed').value
        self.max_angular_speed = self.get_parameter('max_angular_speed').value
        self.current = None
        self.goal = None
        self.state = 'idle'
        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(Odometry, '/odom', self.odom_callback, 10)
        self.create_subscription(PoseStamped, '/goal_pose', self.goal_callback, 10)
        self.create_timer(0.05, self.control_loop)

    @staticmethod
    def yaw_from_quaternion(q):
        return math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                          1.0 - 2.0 * (q.y * q.y + q.z * q.z))

    def odom_callback(self, msg):
        self.current = (msg.pose.pose.position.x, msg.pose.pose.position.y,
                        self.yaw_from_quaternion(msg.pose.pose.orientation))

    def goal_callback(self, msg):
        yaw = self.yaw_from_quaternion(msg.pose.orientation)
        self.goal = (msg.pose.position.x, msg.pose.position.y, yaw)
        self.state = 'rotate_initial'
        self.get_logger().info(
            f'Novo alvo: x={self.goal[0]:.2f}, y={self.goal[1]:.2f}, yaw={self.goal[2]:.2f}')

    def limited(self, value, limit):
        return max(-limit, min(limit, value))

    def control_loop(self):
        if self.current is None or self.goal is None:
            return
        x, y, theta = self.current
        gx, gy, gtheta = self.goal
        cmd = Twist()
        target_heading = math.atan2(gy - y, gx - x)
        if self.state == 'rotate_initial':
            error = wrap_angle(target_heading - theta)
            if abs(error) <= self.yaw_tolerance or math.hypot(gx - x, gy - y) <= self.position_tolerance:
                self.state = 'translate'
                self.get_logger().info('Rotação inicial concluída; iniciando translação.')
            else:
                cmd.angular.z = self.limited(self.kp_rotate * error, self.max_angular_speed)
        elif self.state == 'translate':
            distance = math.hypot(gx - x, gy - y)
            if distance <= self.position_tolerance:
                self.state = 'rotate_final'
                self.get_logger().info('Posição alcançada; iniciando rotação final.')
            else:
                heading_error = wrap_angle(target_heading - theta)
                cmd.linear.x = self.limited(self.kp_translate * distance, self.max_linear_speed)
                cmd.angular.z = self.limited(self.kp_rotate * heading_error, self.max_angular_speed)
        elif self.state == 'rotate_final':
            error = wrap_angle(gtheta - theta)
            if abs(error) <= self.yaw_tolerance:
                self.state = 'idle'
                self.get_logger().info('Manobra concluída.')
            else:
                cmd.angular.z = self.limited(self.kp_rotate * error, self.max_angular_speed)
        self.pub_cmd.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = ManeuverPoseNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
