import math
import sys
import time

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

class GamePacket(BaseAgent):

    def distanceToBall(self, value):
        return math.sqrt(abs(value.x)**2 + abs(value.y)**2)

    def recover(self, target = None):                           #Default target is the ball, but should later be changed to simply match current velocity
        if self.car_height > 20:
            if self.my_car.physics.rotation.roll > 0.3:
                self.roll = -1
            elif self.my_car.physics.rotation.roll < -0.3:
                self.roll = 1
            elif self.my_car.physics.rotation.pitch > 0.1:
                self.pitch = 1
            elif self.my_car.physics.rotation.pitch < -0.1:
                self.pitch = -1
            
    def onWall(self):
        if -4000 < self.car_location.x < 4000:
            if -2000 < self.car_location.y < 2000:
                self.withinBoundaries = True

    def facingBall(self):
        if -0.1 < self.steer_correction_radians < 0.1:
            self.isFacingBall = True

    def steerToBall(self):
        if self.steer_correction_radians > 0.1:     # Positive radians in the unit circle is a turn to the left.
            self.turn = -1                               # Negative value for a turn to the left.
            self.yaw = -1
            self.action_display = "turn left"
            if self.steer_correction_radians > 1.5:
                self.powerslide = True
                self.boost = False
        elif self.steer_correction_radians < -0.1:
            self.turn = 1
            self.yaw = 1
            self.action_display = "turn right"
            if self.steer_correction_radians < -1.5:
                self.powerslide = True
                self.boost = False
        else:
            self.turn = 0
            self.powerslide = False
    
    def dodge(self, delay = 0.1):
        self.jump = True
        self.jumpTriggerTime = time.time() + delay


    def initialize_agent(self):

        #This runs once before the bot starts up
        self.controller_state = SimpleControllerState()
        self.jumpTriggerTime = 0

        # State Values
        self.state = "Chase"

        # Values that must reset before logic is reapplied
        self.jump = False
        self.roll = 0
        self.powerslide = False
        self.pitch = 0
        self.turn = 0
        self.boost = True
        self.yaw = 0
        self.withinBoundaries = False
        self.isFacingBall = False
        
    
    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:

        # New values after each tick
        self.ball_height = packet.game_ball.physics.location.z
        self.ball_location = Vector2(packet.game_ball.physics.location.x, packet.game_ball.physics.location.y)
        self.my_car = packet.game_cars[self.index]
        self.car_location = Vector2(self.my_car.physics.location.x, self.my_car.physics.location.y)
        self.car_height = self.my_car.physics.location.z
        self.car_direction = get_car_facing_vector(self.my_car)
        self.car_to_ball = self.ball_location - self.car_location
        self.distance_to_ball = self.distanceToBall(self.car_to_ball)
        self.steer_correction_radians = self.car_direction.correction_to(self.car_to_ball)
        self.onWall()                       #Sets withinBoundaries
        self.jumped = self.my_car.jumped
        self.doubleJumped = self.my_car.double_jumped
        self.facingBall()

        # Current console printing logic

        #Bot Logic
        if self.state == "Recovery":
            if self.car_height > 200 and self.withinBoundaries:
                self.recover()
            else:
                self.state = "Chase"

        elif self.state == "Dodging":
            if time.time() > self.jumpTriggerTime:
                if self.jumped:
                    if self.doubleJumped == False:
                        self.jump = True
                        self.pitch = -1
                        self.jumpTriggerTime = math.inf
                        self.state = "Chase"
            else:
                self.jump = False

        elif self.state == "Chase":
            self.steerToBall()
            if self.jumped == False:
                if self.distance_to_ball < 300 and self.ball_height < 200:
                    self.dodge()
                    self.state = "Dodging"
                elif self.distance_to_ball > 500 and self.car_height < 20 and self.isFacingBall:
                    self.dodge()
                    self.state = "Dodging"
            elif self.car_height > 200 and self.withinBoundaries:
                self.state = "Recovery"


        self.controller_state.handbrake = self.powerslide
        self.controller_state.throttle = 1.0
        self.controller_state.steer = self.turn
        self.controller_state.jump = self.jump
        self.controller_state.pitch = self.pitch
        self.controller_state.boost = self.boost
        self.controller_state.roll = self.roll
        self.controller_state.yaw = self.yaw

        self.action_display = self.state

        draw_debug(self.renderer, self.my_car, packet.game_ball, self.action_display)

        return self.controller_state

class Vector2:
    def __init__(self, x=0, y=0):
        self.x = float(x)
        self.y = float(y)

    def __add__(self, val):
        return Vector2(self.x + val.x, self.y + val.y)

    def __sub__(self, val):
        return Vector2(self.x - val.x, self.y - val.y)

    def correction_to(self, ideal):
        # The in-game axes are left handed, so use -x
        current_in_radians = math.atan2(self.y, -self.x)
        ideal_in_radians = math.atan2(ideal.y, -ideal.x)

        correction = ideal_in_radians - current_in_radians

        # Make sure we go the 'short way'
        if abs(correction) > math.pi:
            if correction < 0:
                correction += 2 * math.pi
            else:
                correction -= 2 * math.pi

        return correction


def get_car_facing_vector(car):
    pitch = float(car.physics.rotation.pitch)
    yaw = float(car.physics.rotation.yaw)

    facing_x = math.cos(pitch) * math.cos(yaw)
    facing_y = math.cos(pitch) * math.sin(yaw)

    return Vector2(facing_x, facing_y)

def draw_debug(renderer, car, ball, action_display):
    renderer.begin_rendering()
    # draw a line from the car to the ball
    renderer.draw_line_3d(car.physics.location, ball.physics.location, renderer.white())
    # print the action that the bot is taking
    renderer.draw_string_3d(car.physics.location, 2, 2, action_display, renderer.white())
    renderer.end_rendering()