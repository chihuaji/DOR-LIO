#!/usr/bin/env python3
"""random_walker.py — 行人随机行走管理器（参数化版，可与 gen_world.py 联动）.

每个人持续发布 cmd_vel_person_i；方向随机切换；撞墙/卡死时瞬间传送回
安全区域并给新速度。参数通过 ROS 私有参数传入：
  ~num_people  ~room_size  ~speed_min  ~speed_max  ~change_dir_time
"""
import math
import random

import rospy
from geometry_msgs.msg import Twist
from gazebo_msgs.msg import ModelStates, ModelState


class SmartWalker:
    def __init__(self):
        self.num = rospy.get_param('~num_people', 10)
        self.room = rospy.get_param('~room_size', 12.0)
        self.speed_min = rospy.get_param('~speed_min', 1.0)
        self.speed_max = rospy.get_param('~speed_max', 1.8)
        self.check_period = rospy.get_param('~check_period', 0.2)
        self.change_dir_time = rospy.get_param('~change_dir_time', 2.5)
        self.safe_radius = self.room / 2.0 - 1.2

        self.pubs = [rospy.Publisher(f'/cmd_vel_person_{i}', Twist, queue_size=1)
                     for i in range(self.num)]
        self.last_positions = {i: None for i in range(self.num)}
        self.time_since_change = {i: 999.0 for i in range(self.num)}
        self.current_cmds = {i: Twist() for i in range(self.num)}
        self.set_state_pub = rospy.Publisher('/gazebo/set_model_state',
                                             ModelState, queue_size=10)
        self.model_states_msg = None
        rospy.Subscriber('/gazebo/model_states', ModelStates, self.state_cb)
        rospy.Timer(rospy.Duration(self.check_period), self.control_loop)
        rospy.loginfo(f'[random_walker] {self.num} people, room {self.room}m')

    def state_cb(self, msg):
        self.model_states_msg = msg

    def respawn(self, i):
        m = ModelState()
        m.model_name = f'dynamic_person_{i}'
        m.pose.position.x = random.uniform(-self.safe_radius, self.safe_radius)
        m.pose.position.y = random.uniform(-self.safe_radius, self.safe_radius)
        m.pose.position.z = 0.0
        m.pose.orientation.w = 1.0
        m.twist = Twist()
        self.set_state_pub.publish(m)

    def control_loop(self, _):
        if self.model_states_msg is None:
            return
        msg = self.model_states_msg
        for i in range(self.num):
            name = f'dynamic_person_{i}'
            if name not in msg.name:
                continue
            idx = msg.name.index(name)
            curr = msg.pose[idx].position
            stuck = False
            if self.last_positions[i] is not None:
                lx, ly = self.last_positions[i]
                if math.hypot(curr.x - lx, curr.y - ly) < 0.15:
                    stuck = True
            self.last_positions[i] = (curr.x, curr.y)

            if stuck:
                self.respawn(i)
                self.last_positions[i] = None
                self.current_cmds[i].linear.x = random.uniform(self.speed_min, self.speed_max)
                self.current_cmds[i].angular.z = random.uniform(-1.2, 1.2)
                self.time_since_change[i] = 0.0
            else:
                self.time_since_change[i] += self.check_period
                if self.time_since_change[i] >= self.change_dir_time:
                    self.current_cmds[i].linear.x = random.uniform(self.speed_min, self.speed_max)
                    self.current_cmds[i].angular.z = random.uniform(-1.2, 1.2)
                    self.time_since_change[i] = 0.0
            self.pubs[i].publish(self.current_cmds[i])


if __name__ == '__main__':
    try:
        rospy.init_node('simlab_random_walker', anonymous=True)
        SmartWalker()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
