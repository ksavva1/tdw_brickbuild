from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw.add_ons.third_person_camera import ThirdPersonCamera
from magnebot import Magnebot, Arm, ActionStatus

class MagnebotStacking(Controller):
    def __init__(self):
        super().__init__(launch_build=True)

    def run(self):
        # Add camera & Magnebot
        camera = ThirdPersonCamera(position={"x": 0, "y": 1.2, "z": -1.5},
                                   look_at={"x": 0, "y": 0.4, "z": 0},
                                   avatar_id="a")

        magnebot = Magnebot(position={"x": -0.75, "y": 0, "z": 0},
                            rotation={"x": 0, "y": 90, "z": 0})

        self.add_ons.extend([camera, magnebot])

        # Object IDs
        table_id = self.get_unique_id()
        grey_box_id = self.get_unique_id()
        red_box_id = self.get_unique_id()

        commands = []
        commands.append(TDWUtils.create_empty_room(12, 12))

        # Add table & boxes
        table_surface_y = 0.38
        commands.extend(self.get_add_physics_object(
            model_name="small_table_green_marble",
            object_id=table_id,
            position={"x": 0, "y": 0, "z": 0},
            scale_factor={"x": 0.8, "y": 0.5, "z": 0.8}
        ))

        box_scale = 0.5
        
        commands.extend(self.get_add_physics_object(
            model_name="iron_box",
            object_id=red_box_id,
            position={"x": -0.30, "y": table_surface_y, "z": 0},
            scale_factor={"x": box_scale, "y": box_scale, "z": box_scale}
        ))
        commands.extend(self.get_add_physics_object(
            model_name="iron_box",
            object_id=grey_box_id,
            position={"x": -0.05, "y": table_surface_y, "z": 0},
            scale_factor={"x": box_scale, "y": box_scale, "z": box_scale}
        ))
        commands.append({"$type": "set_mass", "id": red_box_id, "mass": 1.0}) #(1kg)
        commands.append({"$type": "set_mass", "id": grey_box_id, "mass": 1.0})

        commands.append({
            "$type": "set_color",
            "color": {"r": 1.0, "g": 0, "b": 0, "a": 1.0}, # Red
            "id": red_box_id
        })

        self.communicate(commands)

        def run_action(name):
            print(f"Action: {name}...")
            while magnebot.action.status == ActionStatus.ongoing:
                self.communicate([])
            self.communicate([])

            if magnebot.action.status != ActionStatus.success:
                # Output failure reason
                print(f"!!! FAILED: {name} | Status: {magnebot.action.status}") 
            else:
                print(f"Success: {name}")

        # ------------------ ACTION SEQUENCE ------------------
        # Slide torso
        magnebot.slide_torso(height=0.8)
        run_action("Adjust Torso")

        # Reach for red box
        magnebot.reach_for(target={"x": -0.30, "y": table_surface_y + 0.05, "z": 0}, 
                           arm=Arm.right)
        run_action("Reach Red Box")

        # Grasp
        magnebot.grasp(target=red_box_id, arm=Arm.right)
        run_action("Grasp Red Box")

        # Lift above grey box
        drop_target_pos = {"x": -0.02, "y": table_surface_y + 0.8, "z": 0}
        magnebot.reach_for(target=drop_target_pos, arm=Arm.right)
        run_action("Move Above Grey Box")

        # Settling phase
        print("Settling physics...")
        for i in range(20):
            self.communicate([])

        # Manual drop
        print("Action: Manual Drop...")
        self.communicate({"$type": "detach_from_magnet", 
                          "id": magnebot.robot_id, 
                          "arm": "right", 
                          "object_id": red_box_id})
        
        for i in range(30):
            self.communicate([])

        # Retract arm avoiding the stack
        retract_target_pos = {"x": -0.40, "y": table_surface_y + 0.5, "z": 0}
        magnebot.reach_for(target=retract_target_pos, arm=Arm.right)
        run_action("Safe Retract")

        # Reset
        magnebot.reset_arm(arm=Arm.right)
        run_action("Reset Arm")
        print("Stacking Complete!")
        
        while True:
            self.communicate([])

if __name__ == "__main__":
    c = MagnebotStacking()
    c.run()