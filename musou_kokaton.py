import math
import os
import random
import sys
import time
import pygame as pg

from math import atan2, degrees


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 1.0),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 1.0),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 1.0),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 1.0),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 1.0),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 1.0),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        # 高速化チェック：左Shiftキーが押されているか
        if key_lst[pg.K_LSHIFT]:
            self.speed = 20  # 高速化
        else:
            self.speed = 10  # 通常速度に戻す
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        if self.state == "hyper": #もしhyperがオンなら
            self.image = pg.transform.laplacian(self.image) #見た目を透明に
            self.hyper_life -= 1 #残り時間減少
            if self.hyper_life < 0: #残り時間が0未満になったら
                self.state = "normal"#hyperをオフに
        screen.blit(self.image, self.rect)
    state = "normal" #初期状態 normal
    hyper_life = 0 #初期のこり時間 0



class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird,angle=0):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        引数　angle:ビームの回転角度
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        initial_angle =math.degrees(math.atan2(-self.vy,self.vx)) + angle
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 2.0)
        self.vx = math.cos(math.radians(initial_angle))
        self.vy = -math.sin(math.radians(initial_angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = random.choice(__class__.imgs)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)



class Shield(pg.sprite.Sprite):
    """こうかとんの前に出現する防御壁"""

    def __init__(self, bird: Bird, life: int):
        super().__init__()
        self.bird = bird
        # 手順1: 壁のサイズ (幅20, 高さ: こうかとんの2倍)
        width, height = 20, bird.rect.height * 2
        self.image = pg.Surface((width, height))
        pg.draw.rect(self.image, (0, 0, 255), (0, 0, width, height))  # 青色の壁
        # 手順2: こうかとんの前に壁を配置
        vx, vy = bird.dire
        angle = degrees(atan2(-vy,vx))
        self.image = pg.transform.rotozoom(self.image, angle, 1.0)
        self.image.set_colorkey((0, 0, 0))
        offset_x, offset_y = vx * width, vy * height
        self.rect = self.image.get_rect(center=(
            bird.rect.centerx + offset_x, 
            bird.rect.centery + offset_y,
        ))
        self.lifetime = 400  # 壁の寿命 (400フレーム)

 
    def update(self):
        """防御壁の寿命を管理"""
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()  # 寿命が尽きたら消滅




class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)

class Gravity(pg.sprite.Sprite):
    """
    重力場に関するクラス
    """
    def __init__(self,life:int):
        """
        重力場Surfaceを生成する
        引数 life：重力場の持続時間
        """
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT))  # 画面全体を覆う
        pg.draw.rect(self.image, (0, 0, 0), (0, 0, WIDTH, HEIGHT))  # (0, 0, 0)は黒色
        self.image.set_alpha(128)  # 透明度を設定
        self.rect = self.image.get_rect()
        self.life = life  # 重力場の持続フレーム数

    def update(self):
        """
        重力場の持続時間を管理し，0未満になったら削除
        """
        self.life -= 1
        if self.life < 0:
            self.kill()  # 重力場を削除



class NeoBeam:
    """
    複数方向にビームを発射するクラス。
    """
    def __init__(self,bird:Bird,num:int):
        """
        NeoBeamクラスの初期化
        引数1bird:ビームを発射するこうかとん
        引数2num:発射するビームの数
        """
        self.beams=self.gen_beams(bird,num)
    
    def gen_beams(self,bird:Bird,num:int) ->list:
        """
        指定されたビーム数だけ異なる角度のビームを生成する。
        """
        beams=[]
        angles=range(-50,51,100//(num-1))  # 角度を等間隔で設定
        for angle in angles:
            beams.append(Beam(bird,angle))
        return beams
        


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()

    bird = Bird(3, (900, 400))
    walls = pg.sprite.Group()  # 防御壁を管理するグループ
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    gravity_fields = pg.sprite.Group()  # 重力場のグループを追加

    emp_active = False
    emp_duration = 100
    score_threshold = 20  # EMP発動に必要な最低スコア

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                beams.add(Beam(bird))
                if key_lst[pg.K_LSHIFT]:
                    beams.add(*NeoBeam(bird,5).beams)
                else:
                    beams.add(Beam(bird))
            if event.type == pg.KEYDOWN and event.key == pg.K_RSHIFT and score.value >= 100: #発動条件：右Shiftキー押下，かつ，スコアが100より大
                bird.state = "hyper" #無敵状態に
                bird.hyper_life = 500 #ライフを500フレームに
                score.value -= 100 #スコアを100減らす

        # 背景の描画を必ず最初に行う

            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN and score.value >= 10:
                # スコアが200以上の場合、RETURNキーで重力場を生成
                gravity_fields.add(Gravity(40))  # 持続時間40フレームの重力場を生成
                score.value -= 10  # スコアを10点消費
            # 防御壁の発動条件: CapsLockキー押下 & スコア50以上 & 壁が存在しない
            if event.type == pg.KEYDOWN and event.key == pg.K_s and len(walls) == 0:
                if score.value >= 50:
                    score.value -= 50  # スコア消費
                    walls.add(Shield(bird, 400))  # 防御壁を生成

        
        screen.blit(bg_img, [0, 0])
        bird.update(key_lst,screen)
        walls.update()

        # 描画処理
        walls.draw(screen)
        screen.blit(bird.image, bird.rect)


        # 敵機の生成
        if tmr % 200 == 0:
            emys.add(Enemy())

        # 敵機の爆弾投下処理
        for emy in emys:
            if emy.state == "stop" and tmr % emy.interval == 0:
                bombs.add(Bomb(emy, bird))

        # 敵機とビームの衝突判定
        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))
            score.value += 10
            bird.change_img(6, screen)

        # 爆弾とビームの衝突判定
        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50))
            score.value += 1


        # こうかとんと爆弾の衝突判定

        # 重力場と爆弾・敵機との衝突判定
        for gravity in gravity_fields:
            for bomb in pg.sprite.spritecollide(gravity, bombs, True):
                exps.add(Explosion(bomb, 50))
            for emy in pg.sprite.spritecollide(gravity, emys, True):
                exps.add(Explosion(emy, 100))


        for bomb in pg.sprite.groupcollide(bombs,walls,True,False).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト

        
        conbomb = pg.sprite.spritecollide(bird, bombs, True) #conbombに接触した爆弾の情報を格納
        if len(conbomb) != 0: #conbombが長さ0以外なら
            if bird.state == "hyper": #無敵なら
                exps.add(Explosion(conbomb[0], 50))  # 爆発エフェクト
                score.value += 1  # 1点アップ
            else:
                bird.change_img(8, screen) # こうかとん悲しみエフェクト
                score.update(screen)
                pg.display.update()
                time.sleep(2)
                return

        if len(pg.sprite.spritecollide(bird, bombs, True)) != 0:
            bird.change_img(8, screen)
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return
        main

        # EMP発動処理
        if key_lst[pg.K_e] and score.value >= score_threshold and not emp_active:
            emp_active = True
            score.value -= 20

        if emp_active:
            emp_duration -= 1
            overlay = pg.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(128)
            overlay.fill((255, 255, 0))
            screen.blit(overlay, (0, 0))
            for emy in emys:
                emy.vx, emy.vy = 0, 0
            for bomb in bombs:
                bomb.speed = 0

            if emp_duration == 0:
                emp_active = False
                emp_duration = 25
                for emy in emys:
                    emy.vy = +6
                for bomb in bombs:
                    bomb.speed = 6

        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        gravity_fields.update()  # 重力場を更新
        gravity_fields.draw(screen)  # 重力場を描画
        score.update(screen)

        pg.display.update()
        tmr += 1
        clock.tick(50)




if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
