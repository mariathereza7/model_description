"""Relative (dead-reckoning) odometry noise model for SLAM experiments."""
import math
import random
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry


class OdomNoiseNode(Node):
    def __init__(self):
        super().__init__('odom_noise_node')
        self.declare_parameter('input_topic', '/diff_drive_base_controller/odom')
        self.declare_parameter('output_topic', '/odom_noisy')
        self.declare_parameter('linear_stddev', 0.003)
        self.declare_parameter('angular_stddev', 0.006)
        random.seed(int(self.declare_parameter('random_seed', 7).value))
        self.last = None
        self.out = None
        self.sub = self.create_subscription(Odometry, self.get_parameter('input_topic').value, self.cb, 20)
        self.pub = self.create_publisher(Odometry, self.get_parameter('output_topic').value, 20)

    @staticmethod
    def yaw(q):
        return math.atan2(2.0 * (q.w*q.z + q.x*q.y), 1.0 - 2.0 * (q.y*q.y + q.z*q.z))

    def cb(self, msg):
        if self.last is None:
            self.last, self.out = msg, msg
            self.pub.publish(msg)
            return
        p0, p1 = self.last.pose.pose.position, msg.pose.pose.position
        dx, dy = p1.x-p0.x, p1.y-p0.y
        dtheta = math.atan2(math.sin(self.yaw(msg.pose.pose.orientation)-self.yaw(self.last.pose.pose.orientation)),
                            math.cos(self.yaw(msg.pose.pose.orientation)-self.yaw(self.last.pose.pose.orientation)))
        ls = float(self.get_parameter('linear_stddev').value)
        aas = float(self.get_parameter('angular_stddev').value)
        out = Odometry(); out.header = msg.header; out.child_frame_id = msg.child_frame_id
        out.pose.pose = self.out.pose.pose
        out.pose.pose.position.x += dx + random.gauss(0.0, ls)
        out.pose.pose.position.y += dy + random.gauss(0.0, ls)
        yaw = self.yaw(self.out.pose.pose.orientation) + dtheta + random.gauss(0.0, aas)
        out.pose.pose.orientation.z, out.pose.pose.orientation.w = math.sin(yaw/2.0), math.cos(yaw/2.0)
        out.twist = msg.twist
        self.last, self.out = msg, out
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = OdomNoiseNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
