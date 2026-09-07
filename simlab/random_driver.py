#!/usr/bin/env python3
"""random_driver.py — 机器人随机巡游驾驶员（雷达车在房间内随机 waypoints 走）.

订阅 /ground_truth/state 获取位姿，向 /cmd_vel 发布速度：
  - 随机选取房间内的目标点，走到附近后换新目标
  - 朝向误差 -> 角速度；距离远 -> 前向速度大
  - 卡死检测（超时未到达/位移过小）-> 倒车 + 换目标
参数：~room_size  ~speed  ~waypoint_margin
"""
import math
import random

import rospy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry


class RandomDriver:
    def __init__(self):
        self.room = rospy.get_param('~room_size', 12.0)
        self.speed = rospy.get_param('~speed', 0.8)
        self.margin = rospy.get_param('~waypoint_margin', 1.5)
        self.rate_hz = rospy.get_param('~rate', 20.0)
        self.reach_tol = rospy.get_param('~reach_tol', 0.6)
        self.wp_timeout = rospy.get_param('~waypoint_timeout', 25.0)

        self.pose = None
        self.yaw = 0.0
        self.target = self.pick_waypoint()
        self.wp_time = 0.0
        self.last_pos = None
        self.stuck_time = 0.0
        self.reverse_until = rospy.Time(0)

        self.pub = rospy.Publisher('/cmd_vel', Twist, queue_size=1)
        rospy.Subscriber('/ground_truth/state', Odometry, self.pose_cb)
        self.timer = rospy.Timer(rospy.Duration(1.0 / self.rate_hz), self.loop)
        rospy.loginfo('[random_driver] random exploration started')

    def pick_waypoint(self):
        half = self.room / 2.0 - self.margin
        return (random.uniform(-half, half), random.uniform(-half, half))

    def pose_cb(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        # yaw from quaternion (z-up)
        self.yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                              1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        self.pose = (p.x, p.y)

    def loop(self, event):
        if self.pose is None:
            return
        cmd = Twist()
        now = event.current_real

        # 倒车脱困阶段
        if now < self.reverse_until:
            cmd.linear.x = -0.4
            cmd.angular.z = 0.9
            self.pub.publish(cmd)
            return

        x, y = self.pose
        tx, ty = self.target
        dist = math.hypot(tx - x, ty - y)

        # 卡死检测：1s 内位移太小
        if self.last_pos is not None:
            if math.hypot(x - self.last_pos[0], y - self.last_pos[1]) < 0.05:
                self.stuck_time += 1.0 / self.rate_hz
                if self.stuck_time > 1.2:
                    self.reverse_until = now + rospy.Duration(1.2)
                    self.stuck_time = 0.0
                    self.target = self.pick_waypoint()
            else:
                self.stuck_time = 0.0
        self.last_pos = (x, y)

        # 到达 / 超时 -> 新目标
        self.wp_time += 1.0 / self.rate_hz
        if dist < self.reach_tol or self.wp_time > self.wp_timeout:
            self.target = self.pick_waypoint()
            self.wp_time = 0.0
            return

        # 朝向目标运动
        desired = math.atan2(ty - y, tx - x)
        err = math.atan2(math.sin(desired - self.yaw), math.cos(desired - self.yaw))
        cmd.angular.z = max(-1.2, min(1.2, 1.5 * err))
        cmd.linear.x = self.speed if abs(err) < 0.5 else self.speed * 0.35
        # 不要贴墙冲：快出界时强制朝房间中心
        half = self.room / 2.0 - 0.8
        if abs(x) > half or abs(y) > half:
            self.target = (random.uniform(-1, 1), random.uniform(-1, 1))
        self.pub.publish(cmd)


if __name__ == '__main__':
    try:
        rospy.init_node('simlab_random_driver', anonymous=True)
        RandomDriver()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
