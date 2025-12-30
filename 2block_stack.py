import json
import numpy as np
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw.add_ons.third_person_camera import ThirdPersonCamera
from magnebot import Magnebot, Arm, ActionStatus

class MagnebotStacking(Controller):
    def __init__(self):
        super().__init__(launch_build=True)

    def run(self):
        # Setup camera
        camera = ThirdPersonCamera(position={"x": 0, "y": 1.5, "z": -1.8},
                                   look_at={"x": 0, "y": 0.5, "z": 0},
                                   avatar_id="a")

        # Setup magnebot
        magnebot = Magnebot(position={"x": -0.7, "y": 0, "z": 0}, 
                            rotation={"x": 0, "y": 90, "z": 0})
        
        self.add_ons.extend([camera, magnebot])

        # Object IDs
        table_id = self.get_unique_id()
        grey_box_id = self.get_unique_id()
        red_box_id = self.get_unique_id()
        
        commands = []
        
        # Create room & table
        commands.append(TDWUtils.create_empty_room(12, 12))
        
        commands.extend(self.get_add_physics_object(model_name="small_table_green_marble",
                                                    object_id=table_id,
                                                    position={"x": 0, "y": 0, "z": 0},
                                                    scale_factor={"x": 0.6, "y": 1.0, "z": 0.6}))

        # 5. Add boxes
        commands.extend(self.get_add_physics_object(model_name="iron_box",
                                                    object_id=red_box_id,
                                                    position={"x": -0.3, "y": 1.0, "z": 0},
                                                    scale_factor={"x": 0.5, "y": 0.5, "z": 0.5}))
        
        commands.extend(self.get_add_physics_object(model_name="iron_box",
                                                    object_id=grey_box_id,
                                                    position={"x": 0.0, "y": 1.0, "z": 0},
                                                    scale_factor={"x": 0.5, "y": 0.5, "z": 0.5}))
        
        commands.append({"$type": "set_color",
                         "color": {"r": 1.0, "g": 0, "b": 0, "a": 1.0},
                         "id": red_box_id})

        self.communicate(commands)
        
        def run_action(name):
            print(f"Action: {name}...")
            while magnebot.action.status == ActionStatus.ongoing:
                self.communicate([])
            self.communicate([]) 
            
            if magnebot.action.status != ActionStatus.success:
                print(f"!!! FAILED: {name} | Reason: {magnebot.action.status}")
                while True: self.communicate([])
            else:
                print(f"Success: {name}")

        # ------------------ ANIMATION SEQUENCE ------------------
        # 1. Slide torso up
        magnebot.slide_torso(height=1.0)
        run_action("Slide Torso Up")

        # 2. Pose arm
        magnebot.reach_for(target={"x": -0.3, "y": 1.35, "z": 0}, arm=Arm.right)
        run_action("Pre-pose Arm")

        # 3. Grasp Red Box
        magnebot.grasp(target=red_box_id, arm=Arm.right)
        run_action("Grasp Red Box")

        # 4. Lift Above Grey Box
        magnebot.reach_for(target={"x": 0.0, "y": 1.45, "z": 0}, arm=Arm.right)
        run_action("Lift Object")

        # 5. Drop
        magnebot.drop(target=grey_box_id, arm=Arm.right)
        run_action("Drop Object")

        # 6. Reset Arm
        magnebot.reset_arm(arm=Arm.right)
        run_action("Reset Arm")

        print("Stacking Complete!")
        while True:
            self.communicate([])

if __name__ == "__main__":
    c = MagnebotStacking()
    c.run()