"""Simple autonomous reactive explorer for the SLAM exercise.

This node does not use an absolute pose or GPS. It only uses LaserScan and
publishes velocity commands to drive the robot through the environment.
"""
import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan


class ExplorerNode(Node):
    def __init__(self):
        super().__init__('explorer_node')
        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('cmd_vel_topic', '/diff_drive_base_controller/cmd_vel_unstamped')
        self.declare_parameter('linear_speed', 0.18)
        self.declare_parameter('turn_speed', 0.65)
        self.declare_parameter('safe_distance', 0.65)
        self.declare_parameter('critical_distance', 0.38)
        self.declare_parameter('turn_time', 1.4)
        self.declare_parameter('control_rate', 10.0)

        self.scan = None
        self.turn_until = 0.0
        self.turn_direction = 1.0
        self.last_scan_time = self.get_clock().now()
        self.sub = self.create_subscription(
            LaserScan, self.get_parameter('scan_topic').value, self.scan_cb,
            qos_profile_sensor_data)
        self.pub = self.create_publisher(
            Twist, self.get_parameter('cmd_vel_topic').value, 10)
        period = 1.0 / float(self.get_parameter('control_rate').value)
        self.timer = self.create_timer(period, self.control)

    def scan_cb(self, msg):
        self.scan = msg
        self.last_scan_time = self.get_clock().now()
        if not hasattr(self, '_scan_reported'):
            self._scan_reported = True
            self.get_logger().info(
                f"Lidar recebido em {self.get_parameter('scan_topic').value}; "
                "iniciando exploração")

    @staticmethod
    def valid_min(values, scan):
        valid = [v for v in values if math.isfinite(v) and scan.range_min <= v <= scan.range_max]
        return min(valid) if valid else scan.range_max

    def sector(self, scan, low, high):
        values = []
        for i, value in enumerate(scan.ranges):
            angle = scan.angle_min + i * scan.angle_increment
            if low <= angle <= high:
                values.append(value)
        return self.valid_min(values, scan)

    def control(self):
        cmd = Twist()
        if self.scan is None:
            self.pub.publish(cmd)
            return

        now = self.get_clock().now().nanoseconds * 1e-9
        scan_age = (self.get_clock().now() - self.last_scan_time).nanoseconds * 1e-9
        if scan_age > 1.0:
            self.get_logger().warn('Lidar sem dados recentes; parando o robô', throttle_duration_sec=2.0)
            self.pub.publish(cmd)
            return

        front = self.sector(self.scan, -0.35, 0.35)
        front_left = self.sector(self.scan, 0.35, 1.15)
        front_right = self.sector(self.scan, -1.15, -0.35)
        left = self.sector(self.scan, 1.15, 2.2)
        right = self.sector(self.scan, -2.2, -1.15)
        critical = float(self.get_parameter('critical_distance').value)
        safe = float(self.get_parameter('safe_distance').value)

        if now < self.turn_until:
            cmd.angular.z = self.turn_direction * float(self.get_parameter('turn_speed').value)
            self.pub.publish(cmd)
            return

        if front < critical or (front_left < critical and front_right < critical):
            self.turn_direction = 1.0 if left >= right else -1.0
            self.turn_until = now + float(self.get_parameter('turn_time').value)
            cmd.angular.z = self.turn_direction * float(self.get_parameter('turn_speed').value)
        elif front < safe:
            self.turn_direction = 1.0 if front_left >= front_right else -1.0
            cmd.linear.x = 0.04
            cmd.angular.z = self.turn_direction * float(self.get_parameter('turn_speed').value)
        else:
            # Small wall-centering correction improves coverage in the simple map.
            cmd.linear.x = float(self.get_parameter('linear_speed').value)
            cmd.angular.z = max(-0.35, min(0.35, 0.18 * (right - left)))

        self.pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = ExplorerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.pub.publish(Twist())
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
