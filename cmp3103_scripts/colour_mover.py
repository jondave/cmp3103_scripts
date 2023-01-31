#!/usr/bin/env python

# An example of TurtleBot 3 subscribe to camera topic and mask colours
# Written for humble
# cv2 image types - http://wiki.ros.org/cv_bridge/Tutorials/ConvertingBetweenROSImagesAndOpenCVImagesPython

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge # Package to convert between ROS and OpenCV Images
import cv2
import numpy as np

class ColourMover(Node):
    def __init__(self):
        super().__init__('colour_mask')
        
        # publish to the image topics for the different images from opencv
        self.pub_video_hsv = self.create_publisher(Image, 'video/hsv', 10)
        self.pub_video_mask = self.create_publisher(Image, 'video/mask', 10)
        self.pub_video_contours = self.create_publisher(Image, 'video/contours', 10)

        # publish cmd_vel topic to move the robot
        self.pub_cmd_vel = self.create_publisher(Twist, 'cmd_vel', 10)

        # subscribe to the camera topic 
        self.sub_camera = self.create_subscription(Image, '/camera/image_raw', self.camera_callback, 10)
        self.sub_camera # prevent unused variable warning

        # Used to convert between ROS and OpenCV images
        self.br = CvBridge()

    def camera_callback(self, data):
        #self.get_logger().info("camera_callback")

        # Convert ROS Image message to OpenCV image
        current_frame = self.br.imgmsg_to_cv2(data, desired_encoding='passthrough')

        # Convert image to HSV
        current_frame_hsv = cv2.cvtColor(current_frame, cv2.COLOR_BGR2HSV)
        # Create mask for range of colours (HSV low values, HSV high values)
        # Onine colour picker - https://redketchup.io/color-picker
        current_frame_mask = cv2.inRange(current_frame_hsv,(70, 0, 50), (150, 255, 255))

        contours, hierarchy = cv2.findContours(current_frame_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # Sort by area (keep only the biggest one)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:1]

        # Draw contour(s) (image to draw on, contours, contour number -1 to draw all contours, colour, thickness):
        current_frame_contours = cv2.drawContours(current_frame, contours, 0, (0, 255, 0), 20)        
        
        if len(contours) > 0:
            M = cv2.moments(contours[0])
            # Centroid
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])
            #print("Centroid of the biggest area: ({}, {})".format(cx, cy))

            # Draw a circle based centered at centroid coordinates
            # cv2.circle(image, center_coordinates, radius, color, thickness) -1 px will fill the circle
            cv2.circle(current_frame, (round(cx), round(cy)), 50, (0, 255, 0), -1)
            
            
            # find height/width of robot camera image from ros2 topic echo /camera/image_raw height: 1080 width: 1920
            self.tw=Twist()

            # if center of object is to the left of image center move right
            if cx < 900:
                self.tw.angular.z=0.3
            # else if center of object is to the right of image center move left
            elif cx >= 1200:
                self.tw.angular.z=-0.3
            else: # center of object is in a 100 px range in the center of the image so dont turn
                #print("object in the center of image")
                self.tw.angular.z=0.0
                
            self.pub_cmd_vel.publish(self.tw)
        else:
            print("No Centroid Found")        

        # Convert OpenCV image to ROS Image message and publish topic
        self.pub_video_hsv.publish(self.br.cv2_to_imgmsg(current_frame_hsv))
        self.pub_video_mask.publish(self.br.cv2_to_imgmsg(current_frame_mask))
        self.pub_video_contours.publish(self.br.cv2_to_imgmsg(cv2.cvtColor(current_frame_contours, cv2.COLOR_BGR2RGB)))
        #self.get_logger().info('Publishing video frame')

def main(args=None):
    print('Starting colour_mover.py.')

    rclpy.init(args=args)

    colour_mover = ColourMover()

    rclpy.spin(colour_mover)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    colour_mover.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
