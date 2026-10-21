"""Regression tests using an ideal differential-drive kinematic model."""
import math
from types import SimpleNamespace

from meu_robo_control.pose_control_node import PoseControlNode


def controller(x=0.0, y=0.0, theta=0.0):
    messages = []
    return SimpleNamespace(
        current_x=x, current_y=y, current_theta=theta,
        goal_x=None, goal_y=None, goal_theta=None, have_odom=True,
        tolerance=0.05, yaw_tolerance=0.05,
        max_linear_speed=0.4, max_angular_speed=1.5,
        kp_x=1.0, kp_y=1.0, kp_theta=2.0,
        pub_cmd=SimpleNamespace(publish=messages.append), messages=messages)


def drive_to(node, target):
    node.goal_x, node.goal_y, node.goal_theta = target
    for _ in range(6000):
        PoseControlNode.control_loop(node)
        cmd = node.messages[-1]
        assert abs(cmd.linear.x) <= node.max_linear_speed
        assert abs(cmd.angular.z) <= node.max_angular_speed
        node.current_x += cmd.linear.x * math.cos(node.current_theta) * 0.05
        node.current_y += cmd.linear.x * math.sin(node.current_theta) * 0.05
        node.current_theta += cmd.angular.z * 0.05
        if cmd.linear.x == 0 and cmd.angular.z == 0:
            break
    assert math.hypot(node.goal_x - node.current_x, node.goal_y - node.current_y) <= node.tolerance
    error = node.goal_theta - node.current_theta
    assert abs(math.atan2(math.sin(error), math.cos(error))) <= node.yaw_tolerance


def test_recovers_from_observed_stall():
    node = controller(0.9627, 0.7939, 0.9176)
    drive_to(node, (2.0, 0.0, 1.57))


def test_all_waypoints_and_target_behind_robot():
    node = controller()
    for target in [(0., 0., 0.), (2., 0., 1.57), (2., 2., 3.14), (0., 2., 0.), (-1., 2., 0.)]:
        drive_to(node, target)


def test_waits_for_odometry():
    node = controller()
    node.goal_x, node.goal_y, node.goal_theta = 1., 0., 0.
    node.have_odom = False
    PoseControlNode.control_loop(node)
    assert not node.messages
