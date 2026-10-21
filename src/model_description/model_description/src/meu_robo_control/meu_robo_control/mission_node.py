"""Publish ordered odometry-frame goals for the pose controller."""

import math

import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node


class MissionNode(Node):
    def __init__(self):
        super().__init__('mission_node')
        # ROS parameters support flat arrays, not nested arrays.
        values = self.declare_parameter(
            'waypoints', [0.0, 0.0, 0.0, 2.0, 0.0, 1.57,
                          2.0, 2.0, 3.14, 0.0, 2.0, 0.0]).value
        self.acc_rad = self.declare_parameter('acc_rad', 0.15).value
        if not values or len(values) % 3 or not all(math.isfinite(v) for v in values):
            raise ValueError('waypoints must contain finite x, y, yaw triples')
        if not math.isfinite(self.acc_rad) or self.acc_rad <= 0:
            raise ValueError('acc_rad must be positive and finite')
        self.waypoints = [values[i:i + 3] for i in range(0, len(values), 3)]
        self.index = 0
        self.odom = None
        self.sent = False
        self.done = False
        self.publisher = self.create_publisher(PoseStamped, '/goal_pose', 10)
        self.subscription = self.create_subscription(Odometry, '/odom', self.on_odom, 10)
        self.timer = self.create_timer(0.1, self.tick)
        self.get_logger().info('Aguardando odometria e controlador de pose.')

    def on_odom(self, msg):
        self.odom = msg

    def tick(self):
        if self.odom is None or self.publisher.get_subscription_count() == 0:
            return
        x, y, yaw = self.waypoints[self.index]
        position = self.odom.pose.pose.position
        if not self.done and self.sent and math.hypot(x - position.x, y - position.y) <= self.acc_rad:
            self.get_logger().info(f'Ponto {self.index + 1} alcançado.')
            if self.index + 1 == len(self.waypoints):
                self.done = True
                self.get_logger().info('Missão concluída; mantendo o último alvo de pose.')
            else:
                self.index += 1
                self.sent = False
                x, y, yaw = self.waypoints[self.index]
        goal = PoseStamped()
        goal.header.stamp = self.get_clock().now().to_msg()
        goal.header.frame_id = self.odom.header.frame_id or 'odom'
        goal.pose.position.x = float(x)
        goal.pose.position.y = float(y)
        goal.pose.orientation.z = math.sin(yaw / 2)
        goal.pose.orientation.w = math.cos(yaw / 2)
        self.publisher.publish(goal)
        if not self.sent:
            self.get_logger().info(f'Alvo {self.index + 1}: x={x}, y={y}, yaw={yaw}')
        self.sent = True


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = MissionNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
