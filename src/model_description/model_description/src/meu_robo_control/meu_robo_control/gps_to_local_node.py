"""Convert GPS latitude/longitude/altitude to a local ENU XYZ frame."""

import math

import rclpy
from geometry_msgs.msg import PointStamped
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix


class GpsToLocalNode(Node):
    """Publish local East-North-Up coordinates from NavSatFix messages."""

    def __init__(self):
        super().__init__('gps_to_local_node')
        self.declare_parameter('origin_latitude', 0.0)
        self.declare_parameter('origin_longitude', 0.0)
        self.declare_parameter('origin_altitude', 0.0)
        self.declare_parameter('earth_radius', 6378137.0)
        self.origin_lat = math.radians(self.get_parameter('origin_latitude').value)
        self.origin_lon = math.radians(self.get_parameter('origin_longitude').value)
        self.origin_alt = self.get_parameter('origin_altitude').value
        self.radius = self.get_parameter('earth_radius').value
        self.publisher = self.create_publisher(PointStamped, '/gps/position_local', 10)
        self.subscription = self.create_subscription(NavSatFix, '/gps/fix', self.callback, 10)

    def callback(self, msg):
        if not (math.isfinite(msg.latitude) and math.isfinite(msg.longitude)
                and math.isfinite(msg.altitude)):
            self.get_logger().warning('GPS inválido; conversão ignorada.')
            return
        lat = math.radians(msg.latitude)
        lon = math.radians(msg.longitude)
        point = PointStamped()
        point.header = msg.header
        point.header.frame_id = 'gps_local'
        point.point.x = (lon - self.origin_lon) * math.cos(self.origin_lat) * self.radius
        point.point.y = (lat - self.origin_lat) * self.radius
        point.point.z = msg.altitude - self.origin_alt
        self.publisher.publish(point)


def main(args=None):
    rclpy.init(args=args)
    node = GpsToLocalNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
