#! /usr/bin/python
#-*- coding: utf-8 -*-

"""
Reverser_NM - 3代目ロボット

【移動戦略】
- 中央3/5範囲を反時計回りで巡回
- WallRunnerとは逆方向で遭遇パターンを変化

【戦闘戦略】
- 体当たり戦略を完全廃止
- 命中確実なタイミングのみ射撃
- 弾命中時のHP回復(+2×弾威力)を活用

【逃走戦略】
- 被弾・衝突時に周回方向を反転
- 敵の追撃経路を撹乱し連続被弾を防止
"""

from robot import Robot
import math

MOVE_STEP = 5
WALL_DISTANCE = 50
BULLET_POWER = 2

# 中央3/5範囲の境界定義（マップサイズの1/5からの距離）
BOUNDARY_RATIO = 1.0 / 5.0

# 移動状態（反時計回り：左→下→右→上）
STATE_MOVING_UNKNOWN = 0
STATE_MOVING_UP      = 1
STATE_MOVING_RIGHT   = 2
STATE_MOVING_DOWN    = 3
STATE_MOVING_LEFT    = 4

# 方向反転用の状態マッピング（時計回り化）
# 反時計回り：左→下→右→上
# 時計回り：左→上→右→下
REVERSE_STATE_MAP = {
    STATE_MOVING_UP:    STATE_MOVING_DOWN,
    STATE_MOVING_DOWN:  STATE_MOVING_UP,
    STATE_MOVING_LEFT:  STATE_MOVING_RIGHT,
    STATE_MOVING_RIGHT: STATE_MOVING_LEFT
}

class Reverser_NM(Robot):
    
    def init(self):
        """ロボットの初期化"""
        
        # ロボットの色設定（紫系：反転・変化を表現）
        self.setColor(138, 43, 226)        # 本体：青紫
        self.setGunColor(186, 85, 211)     # 銃：ミディアムオーキッド
        self.setRadarColor(218, 112, 214)  # レーダー：オーキッド
        self.setBulletsColor(255, 0, 255)  # 弾：マゼンタ

        self.radarVisible(True)
        self.lockRadar("gun")
        self.setRadarField("thin")
        
        # マップサイズを取得
        self.areaSize = self.getMapSize()
        # 中央3/5領域の境界（幅と高さそれぞれの1/5地点）
        self.WALL_DISTANCE_X = self.areaSize.width() * BOUNDARY_RATIO
        self.WALL_DISTANCE_Y = self.areaSize.height() * BOUNDARY_RATIO
        
        # 初期状態：反時計回りで下向きからスタート
        self.state = STATE_MOVING_UNKNOWN
        self.is_reversed = False  # 反転状態フラグ
        
        # 敵検出情報
        self.enemy_detected = False
        self.enemy_distance = float('inf')
        self.enemy_angle = 0
        self.enemy_position = None
    
    def myTurn(self, angle):
        """本体と銃を同時に回転"""
        self.turn(angle)
        self.gunTurn(angle)
    
    def run(self):
        """メインループ - Collider_NMスタイルの安全な移動制御"""
        pos = self.getPosition()
        angle = self.getHeading() % 360
        
        # 反時計回り（デフォルト）: 左→下→右→上
        # 時計回り（反転時）: 左→上→右→下
        if self.state == STATE_MOVING_UNKNOWN:
            # 初期状態: まず完全停止してから方向を調整
            self.stop()
            self.myTurn(-angle)  # 下向き(0度)に調整
            self.state = STATE_MOVING_DOWN
        elif self.state == STATE_MOVING_UP:
            if pos.y() < self.WALL_DISTANCE_Y:
                self.rPrint("Reached upper boundary")
                self.stop()
                # 境界から離れるため少し下に移動
                self.move(MOVE_STEP * 2)
                if not self.is_reversed:
                    # 反時計回り: 上→右
                    self.myTurn(-90)
                    self.state = STATE_MOVING_RIGHT
                else:
                    # 時計回り: 上→左
                    self.myTurn(90)
                    self.state = STATE_MOVING_LEFT
            else:
                self.move(MOVE_STEP)
        elif self.state == STATE_MOVING_DOWN:
            if pos.y() > (self.areaSize.height() - self.WALL_DISTANCE_Y):
                self.rPrint("Reached lower boundary")
                self.stop()
                # 境界から離れるため少し上に移動
                self.move(-MOVE_STEP * 2)
                if not self.is_reversed:
                    # 反時計回り: 下→左
                    self.myTurn(-90)
                    self.state = STATE_MOVING_LEFT
                else:
                    # 時計回り: 下→右
                    self.myTurn(90)
                    self.state = STATE_MOVING_RIGHT
            else:
                self.move(MOVE_STEP)
        elif self.state == STATE_MOVING_LEFT:
            if pos.x() < self.WALL_DISTANCE_X:
                self.rPrint("Reached left boundary")
                self.stop()
                # 境界から離れるため少し右に移動
                self.move(MOVE_STEP * 2)
                if not self.is_reversed:
                    # 反時計回り: 左→下
                    self.myTurn(-90)
                    self.state = STATE_MOVING_DOWN
                else:
                    # 時計回り: 左→上
                    self.myTurn(90)
                    self.state = STATE_MOVING_UP
            else:
                self.move(MOVE_STEP)
        elif self.state == STATE_MOVING_RIGHT:
            if pos.x() > (self.areaSize.width() - self.WALL_DISTANCE_X):
                self.rPrint("Reached right boundary")
                self.stop()
                # 境界から離れるため少し左に移動
                self.move(-MOVE_STEP * 2)
                if not self.is_reversed:
                    # 反時計回り: 右→上
                    self.myTurn(-90)
                    self.state = STATE_MOVING_UP
                else:
                    # 時計回り: 右→下
                    self.myTurn(90)
                    self.state = STATE_MOVING_DOWN
            else:
                self.move(MOVE_STEP)

    def onHitWall(self):
        """壁衝突時の処理 - 本来は起きないはずだが念のため"""
        self.rPrint("Hit wall unexpectedly!")
        self.move( -2 * self.WALL_DISTANCE_Y)
        self.reset()
        # 状態をリセット
        self.state = STATE_MOVING_UNKNOWN
        self.reset()
        self.rPrint(f"Boundary distance X: {self.WALL_DISTANCE_X:.1f}, Y: {self.WALL_DISTANCE_Y:.1f}")
        

    def sensors(self):
        """センサー処理（必須メソッド）"""
        pass

    def onRobotHit(self, robotId, robotName):
        """他のロボットに衝突した時 - 体当たり戦略は廃止、即離脱"""
        self.rPrint(f'Collision with: {robotId}')
        # 衝突時は方向反転して逃走
        self.reverse_direction()
        self.stop()

    def onHitByRobot(self, robotId, robotName):
        """他のロボットに衝突された時"""
        self.rPrint("Collided by another bot!")
        # 衝突時は方向反転して逃走
        self.reverse_direction()
        self.stop()

    def onHitByBullet(self, bulletBotId, bulletBotName, bulletPower):
        """弾に当たった時"""
        self.rPrint(f"Hit by {bulletBotId} with power: {bulletPower}")
        
        # 被弾時は方向反転して逃走
        self.reverse_direction()
        self.stop()
        self.setRadarField("large")

    def onBulletHit(self, botId, bulletId):
        """自分の弾が当たった時"""
        self.rPrint(f"Hit target: {botId}")
        # HP回復が発生したことを記録
        self.rPrint("HP recovered!")
        
        # 一旦停止、センサーを補足して確実に狙う
        self.stop()
        self.setRadarField("thin")

    def onBulletMiss(self, bulletId):
        """弾が外れた時"""
        self.rPrint(f"Bullet {bulletId} missed")
        # self.gunTurn(30)
        self.setRadarField("normal")

    def onRobotDeath(self):
        """自分が破壊された時"""
        self.rPrint("Destroyed!")
    
    def onTargetSpotted(self, botId, botName, botPos):
        """レーダーで敵を発見した時 - 即座に射撃（命中重視）"""
        # 敵の位置情報を更新
        pos = self.getPosition()
        dx = botPos.x() - pos.x()
        dy = botPos.y() - pos.y()
        
        # 距離を計算
        self.enemy_distance = math.sqrt(dx * dx + dy * dy)
        self.enemy_angle = math.degrees(math.atan2(-dx, dy)) % 360
        self.enemy_detected = True
        self.enemy_position = botPos
        
        # 近距離または中距離で命中が見込める場合のみ射撃
        if self.enemy_distance < 300:
            current_gun = self.getGunHeading()
            gun_error = abs((self.enemy_angle - current_gun + 180) % 360 - 180)
            
            # 銃口が敵の方向を向いている（レーダーと銃がロックされているので精度高い）
            if gun_error < 15:
                self.fire(BULLET_POWER)
                self.rPrint(f"Fired at {botId} (distance: {self.enemy_distance:.1f})")
    
    def reverse_direction(self):
        """周回方向を反転"""
        self.is_reversed = not self.is_reversed
        direction_name = "clockwise" if self.is_reversed else "counter-clockwise"
        self.rPrint(f"Direction reversed to {direction_name}")