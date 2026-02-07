from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw.add_ons.third_person_camera import ThirdPersonCamera
from magnebot import Magnebot, Arm, ActionStatus


class MagnebotStacking4(Controller):

    # ── geometry ──────────────────────────────────────────────────────
    TABLE_SURFACE_Y = 0.42
    SPAWN_Y         = 0.46
    BOX_SCALE       = 0.5
    BOX_FULL_H      = 0.12
    CRUISE_ALT      = 1.20
    GRASP_DY        = 0.02
    DROP_CLEARANCE  = 0.15

    # stack target on the table
    STACK_X = 0.0
    STACK_Z = 0.0

    # starting positions
    BLOCK_STARTS = [
        {"x": -0.20, "z":  0.20},   # Red
        {"x": -0.20, "z": -0.20},   # Blue
        {"x":  0.20, "z":  0.20},   # Green
        {"x":  0.20, "z": -0.20},   # Yellow
    ]

    BLOCK_COLORS = [
        {"r": 0.90, "g": 0.10, "b": 0.10, "a": 1.0},
        {"r": 0.15, "g": 0.15, "b": 0.90, "a": 1.0},
        {"r": 0.10, "g": 0.75, "b": 0.15, "a": 1.0},
        {"r": 0.95, "g": 0.80, "b": 0.10, "a": 1.0},
    ]

    def __init__(self):
        super().__init__(launch_build=True)

    def _settle(self, n: int = 25):
        for _ in range(n):
            self.communicate([])

    def _do(self, bot: Magnebot, label: str):
        """Block until current Magnebot action completes."""
        print(f"  ▸ {label} …")
        while bot.action.status == ActionStatus.ongoing:
            self.communicate([])
        self.communicate([])
        status = bot.action.status
        tag = "✔" if status == ActionStatus.success else "✘"
        print(f"    {tag} {status}")


    def run(self):

        camera = ThirdPersonCamera(
            position={"x": 1.1, "y": 1.6, "z": -1.3},
            look_at={"x": 0, "y": 0.55, "z": 0},
            avatar_id="obs",
        )
        bot = Magnebot(
            position={"x": -0.85, "y": 0, "z": 0},
            rotation={"x": 0, "y": 90, "z": 0},
        )
        self.add_ons.extend([camera, bot])

        # ────── scene + objects ──────────────────────────────────────────
        table_id  = self.get_unique_id()
        block_ids = [self.get_unique_id() for _ in range(4)]

        cmds = [TDWUtils.create_empty_room(12, 12)]

        # Table
        cmds.extend(self.get_add_physics_object(
            model_name="small_table_green_marble",
            object_id=table_id,
            position={"x": 0, "y": 0, "z": 0},
            scale_factor={"x": 0.8, "y": 0.5, "z": 0.8},
        ))

        # Spawn blocks
        for i in range(4):
            bx = self.BLOCK_STARTS[i]["x"]
            bz = self.BLOCK_STARTS[i]["z"]
            cmds.extend(self.get_add_physics_object(
                model_name="iron_box",
                object_id=block_ids[i],
                position={"x": bx, "y": self.SPAWN_Y, "z": bz},
                scale_factor={"x": self.BOX_SCALE,
                              "y": self.BOX_SCALE,
                              "z": self.BOX_SCALE},
            ))
            cmds.append({"$type": "set_mass", "id": block_ids[i], "mass": 0.8})
            cmds.append({"$type": "set_color",
                         "color": self.BLOCK_COLORS[i],
                         "id": block_ids[i]})

        self.communicate(cmds)
        # Let blocks settle
        self._settle(50)

        # ── stacking loop ─────────────────────────────────────────────
        for i, bid in enumerate(block_ids):

            bx = self.BLOCK_STARTS[i]["x"]
            bz = self.BLOCK_STARTS[i]["z"]

            # Where the top of the stack currently is
            stack_top_y = self.TABLE_SURFACE_Y + i * self.BOX_FULL_H

            print(f"\n{'='*55}")
            print(f"  BLOCK {i}  │  layer {i}  │  yaw {90*i}°")
            print(f"{'='*55}")

            # 1 ─ Raise torso progressively for each layer
            torso_h = 0.6 + i * 0.15
            bot.slide_torso(height=min(torso_h, 1.5))
            self._do(bot, "Adjust torso")

            # 2 ─ Reach down to the block on the table
            #      Target = block starting position + small y lift
            grasp_y = self.TABLE_SURFACE_Y + self.GRASP_DY
            bot.reach_for(
                target={"x": bx, "y": grasp_y, "z": bz},
                arm=Arm.right,
            )
            self._do(bot, "Reach for block")

            # 3 ─ Grasp
            bot.grasp(target=bid, arm=Arm.right)
            self._do(bot, "Grasp")
            self._settle(10)

            # 4 ─ Lift straight up
            bot.reach_for(
                target={"x": bx, "y": self.CRUISE_ALT, "z": bz},
                arm=Arm.right,
            )
            self._do(bot, "Lift up")

            # 5 ─ Translate laterally to above stack centre
            bot.reach_for(
                target={"x": self.STACK_X,
                        "y": self.CRUISE_ALT,
                        "z": self.STACK_Z},
                arm=Arm.right,
            )
            self._do(bot, "Move above stack")

            # 6 ─ Lower to drop position
            drop_y = stack_top_y + self.DROP_CLEARANCE
            bot.reach_for(
                target={"x": self.STACK_X,
                        "y": drop_y,
                        "z": self.STACK_Z},
                arm=Arm.right,
            )
            self._do(bot, "Lower to drop height")
            self._settle(15)

            # 7 ─ Release
            print("  ▸ Releasing …")
            self.communicate({"$type": "detach_from_magnet",
                              "id": bot.robot_id,
                              "arm": "right",
                              "object_id": bid})
            self._settle(50)     # generous settle for drop

            # 8 ─ Snap block to exact stack pose ─────────────────────
            #     Layer n sits on TABLE_SURFACE_Y + n * BOX_FULL_H.
            place_y = self.TABLE_SURFACE_Y + i * self.BOX_FULL_H
            snap_cmds = [
                {"$type": "teleport_object",
                 "id": bid,
                 "position": {"x": self.STACK_X,
                              "y": place_y,
                              "z": self.STACK_Z}},
                {"$type": "rotate_object_to",          # reset rotation first
                 "rotation": {"x": 0, "y": 0, "z": 0, "w": 1},
                 "id": bid},
            ]
            self.communicate(snap_cmds)

            # Apply yaw = 90 * i degrees
            if i > 0:
                self.communicate([
                    {"$type": "rotate_object_by",
                     "angle": 90.0 * i,
                     "axis": "yaw",
                     "id": bid,
                     "is_world": True},
                ])

            # 9 ─ Freeze the block so tower can't topple
            self.communicate([
                {"$type": "set_kinematic_state",
                 "id": bid,
                 "is_kinematic": True,
                 "use_gravity": False},
            ])
            self._settle(10)
            print(f"    ✔ Block {i} locked at y={place_y:.3f}, yaw={90*i}°")

            # 10 ─ Retract arm
            bot.reach_for(
                target={"x": self.STACK_X,
                        "y": self.CRUISE_ALT,
                        "z": self.STACK_Z},
                arm=Arm.right,
            )
            self._do(bot, "Retract up")

            bot.reach_for(
                target={"x": -0.50, "y": self.CRUISE_ALT, "z": 0},
                arm=Arm.right,
            )
            self._do(bot, "Retract lateral")

            # 11 ─ Reset arm
            bot.reset_arm(arm=Arm.right)
            self._do(bot, "Reset arm")
            self._settle(20)

        # ── finish ───────────────────────────────────────────────────
        print(f"\n{'='*55}")
        print("  ✅  ")
        print(f"{'='*55}\n")

        while True:
            self.communicate([])


if __name__ == "__main__":
    c = MagnebotStacking4()
    c.run()