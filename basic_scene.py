from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw.add_ons.third_person_camera import ThirdPersonCamera
from magnebot import Magnebot

class MagnebotScene(Controller):
    def __init__(self):
        super().__init__(launch_build=True)

    def run(self):
        # Setup camera
        camera = ThirdPersonCamera(position={"x": 2.5, "y": 2.0, "z": -2.5},
                                   look_at={"x": 0, "y": 0, "z": 0},
                                   avatar_id="a")
        #Setup Magnebot
        magnebot = Magnebot(position={"x": -1.5, "y": 0, "z": 0})
        
        self.add_ons.extend([camera, magnebot])

        # Static object IDs
        table_id = self.get_unique_id()
        box1_id = self.get_unique_id()
        box2_id = self.get_unique_id()
        
        commands = []
        
        # Create room
        commands.append(TDWUtils.create_empty_room(12, 12))
        
        # Add table
        commands.extend(self.get_add_physics_object(model_name="small_table_green_marble",
                                                    object_id=table_id,
                                                    position={"x": 0, "y": 0, "z": 0}))

        # Add Boxes
        commands.extend(self.get_add_physics_object(model_name="iron_box",
                                                    object_id=box1_id,
                                                    position={"x": -0.3, "y": 1.0, "z": 0}))

        commands.extend(self.get_add_physics_object(model_name="iron_box",
                                                    object_id=box2_id,
                                                    position={"x": 0.3, "y": 1.0, "z": 0}))
        commands.append({"$type": "set_color",
                         "color": {"r": 1.0, "g": 0, "b": 0, "a": 1.0},
                         "id": box2_id})

        self.communicate(commands)
        print("Scene loaded")

        # Keep window open
        while True:
            self.communicate([])

if __name__ == "__main__":
    c = MagnebotScene()
    c.run()