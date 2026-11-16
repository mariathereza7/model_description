import math
import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node


class RmseNode(Node):
    def __init__(self):
        super().__init__('rmse_node')
        self.sum_sq = 0.0
        self.samples = 0
        self.create_subscription(PoseStamped, '/ref_pose', self.ref_cb, 10)
        self.create_subscription(PoseStamped, '/real_pose', self.real_cb, 10)
        self.ref = None
        self.timer = self.create_timer(5.0, self.report)

    def ref_cb(self, msg):
        self.ref = (msg.pose.position.x, msg.pose.position.y)

    def real_cb(self, msg):
        if self.ref is None:
            return
        dx = self.ref[0] - msg.pose.position.x
        dy = self.ref[1] - msg.pose.position.y
        self.sum_sq += dx * dx + dy * dy
        self.samples += 1

    def report(self):
        if self.samples:
            rmse = math.sqrt(self.sum_sq / self.samples)
            self.get_logger().info(f'RMSE de posição: {rmse:.6f} m ({self.samples} amostras)')


def main(args=None):
    rclpy.init(args=args)
    node = RmseNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
