import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry, Path
from .control_utils import wrap_angle, yaw_from_quaternion
from .pid import PID

class TrajectoryNode(Node):
    def __init__(self):
        super().__init__('trajectory_node')
        
        self.declare_parameter('A', 1.0)
        self.declare_parameter('B', 2.0)
        self.declare_parameter('omega', 0.5)
        self.declare_parameter('k_ff', 1.0) # 0.0 para malha fechada pura, 1.0 para feedforward
        self.declare_parameter('open_loop', False) # True para malha aberta pura
        self.declare_parameter('kp_x', 1.0)
        self.declare_parameter('kp_y', 2.0)
        self.declare_parameter('kp_theta', 2.0)
        self.declare_parameter('ki_x', 0.0)
        self.declare_parameter('ki_y', 0.0)
        self.declare_parameter('ki_theta', 0.0)
        self.declare_parameter('kd_x', 0.0)
        self.declare_parameter('kd_y', 0.0)
        self.declare_parameter('kd_theta', 0.0)
        self.declare_parameter('integral_limit', 1.0)
        self.declare_parameter('max_linear_speed', 1.0)
        self.declare_parameter('max_angular_speed', 2.0)
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')

        self.A = self.get_parameter('A').value
        self.B = self.get_parameter('B').value
        self.W = self.get_parameter('omega').value
        self.k_ff = self.get_parameter('k_ff').value
        self.open_loop = self.get_parameter('open_loop').value

        self.x = self.y = self.theta = 0.0
        self.have_odom = False
        lim = self.get_parameter('integral_limit').value
        self.pid_x = PID(self.get_parameter('kp_x').value, self.get_parameter('ki_x').value, self.get_parameter('kd_x').value, lim)
        self.pid_y = PID(self.get_parameter('kp_y').value, self.get_parameter('ki_y').value, self.get_parameter('kd_y').value, lim)
        self.pid_theta = PID(self.get_parameter('kp_theta').value, self.get_parameter('ki_theta').value, self.get_parameter('kd_theta').value, lim)
        self.sub_odom = self.create_subscription(Odometry, '/odom', self.odom_cb, 10)
        self.pub_cmd = self.create_publisher(Twist, self.get_parameter('cmd_vel_topic').value, 10)
        self.pub_ref_pose = self.create_publisher(PoseStamped, '/ref_pose', 10)
        self.pub_real_pose = self.create_publisher(PoseStamped, '/real_pose', 10)
        self.pub_ref_path = self.create_publisher(Path, '/trajectory_reference', 10)
        self.pub_real_path = self.create_publisher(Path, '/trajectory_real', 10)
        self.declare_parameter('max_path_length', 2000)
        self.max_path_length = int(self.get_parameter('max_path_length').value)
        self.reference_path = Path()
        self.reference_path.header.frame_id = 'odom'
        self.real_path = Path()
        self.real_path.header.frame_id = 'odom'

        self.t = 0.0
        self.dt = 0.05
        self.start_time = None
        self.last_time = None
        self.timer = self.create_timer(self.dt, self.loop)

    def odom_cb(self, msg):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
        self.theta = yaw_from_quaternion(msg.pose.pose.orientation)
        self.have_odom = True

    def loop(self):
        now = self.get_clock().now()
        if self.start_time is None:
            self.start_time = now
            self.last_time = now
        elapsed = (now - self.start_time).nanoseconds * 1.0e-9
        dt = (now - self.last_time).nanoseconds * 1.0e-9
        self.last_time = now
        if dt <= 0.0 or dt > 1.0:
            dt = self.dt
        self.t = elapsed

        # 1. Referência em oito: x=A sin(wt), y=B/2 sin(2wt).
        xd = self.A * math.sin(self.W * self.t)
        yd = (self.B / 2.0) * math.sin(2 * self.W * self.t)
        
        dxd = self.A * self.W * math.cos(self.W * self.t)
        dyd = self.B * self.W * math.cos(2 * self.W * self.t)
        
        ddxd = - self.A * (self.W**2) * math.sin(self.W * self.t)
        ddyd = -2 * self.B * (self.W**2) * math.sin(2 * self.W * self.t)

        thetad = math.atan2(dyd, dxd)
        
        # 2. Termos Feedforward (Malha Aberta)
        v_ff = math.sqrt(dxd**2 + dyd**2)
        w_ff = (ddyd * dxd - ddxd * dyd) / (dxd**2 + dyd**2 + 1e-6)

        if self.open_loop:
            v_cmd = v_ff
            w_cmd = w_ff
        else:
            v_cmd = 0.0
            w_cmd = 0.0
            if self.have_odom:
                ex_i = xd - self.x
                ey_i = yd - self.y
                etheta = wrap_angle(thetad - self.theta)
                ex_b = math.cos(self.theta)*ex_i + math.sin(self.theta)*ey_i
                ey_b = -math.sin(self.theta)*ex_i + math.cos(self.theta)*ey_i
                # Lei de seguimento para robô unicycle:
                # o feedforward linear é projetado na direção atual do robô;
                # o erro angular usa sin(theta), evitando descontinuidades em pi.
                v_cmd = self.k_ff * v_ff * math.cos(etheta) + self.pid_x.update(ex_b, dt)
                w_cmd = (self.k_ff * w_ff
                         + self.pid_y.update(ey_b, dt)
                         + self.pid_theta.update(math.sin(etheta), dt))

        v_limit = self.get_parameter('max_linear_speed').value
        w_limit = self.get_parameter('max_angular_speed').value
        v_cmd = max(-v_limit, min(v_cmd, v_limit))
        w_cmd = max(-w_limit, min(w_cmd, w_limit))

        ref = PoseStamped(); ref.header.stamp = self.get_clock().now().to_msg(); ref.header.frame_id = 'odom'
        ref.pose.position.x, ref.pose.position.y = xd, yd
        ref.pose.orientation.z, ref.pose.orientation.w = math.sin(thetad / 2.0), math.cos(thetad / 2.0)
        self.pub_ref_pose.publish(ref)
        self.reference_path.header.stamp = ref.header.stamp
        self.reference_path.poses.append(ref)
        if len(self.reference_path.poses) > self.max_path_length:
            self.reference_path.poses = self.reference_path.poses[-self.max_path_length:]
        self.pub_ref_path.publish(self.reference_path)
        if self.have_odom:
            real = PoseStamped(); real.header = ref.header
            real.pose.position.x, real.pose.position.y = self.x, self.y
            real.pose.orientation.z, real.pose.orientation.w = math.sin(self.theta / 2.0), math.cos(self.theta / 2.0)
            self.pub_real_pose.publish(real)
            self.real_path.header.stamp = real.header.stamp
            self.real_path.poses.append(real)
            if len(self.real_path.poses) > self.max_path_length:
                self.real_path.poses = self.real_path.poses[-self.max_path_length:]
            self.pub_real_path.publish(self.real_path)

        cmd = Twist()
        cmd.linear.x = v_cmd
        cmd.angular.z = w_cmd
        self.pub_cmd.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = TrajectoryNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
