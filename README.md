## VideoEditAPP

VideoEditApp は、動画のアップロード、チャンク送信、結合、エンコードを行うウェブアプリケーションです。ユーザーは動画をアップロードし、指定した操作（圧縮、解像度変更、アスペクト比変更、音声抽出、GIF作成、WebM作成など）を適用することができます。処理後の動画はダウンロード可能です。

リンク先:https://videoeditapp.yuta-kimu.com 

![image](https://github.com/user-attachments/assets/db094252-575c-4592-a9e0-73b9251b558c)


## 技術スタック
#### フロントエンド
HTML5:ユーザーインターフェースの構築 \
JavaScript: クライアントサイドのインタラクションとチャンクアップロードの実装。 \
Bootstrap: レスポンシブデザインのためのCSSフレームワーク。 \

#### バックエンド
Python(Flask) \
Gunicorn: WSGI HTTP サーバーとして Flask アプリケーションを実行。\
systemd: Gunicorn のプロセスマネージャーとして使用。\
ffmpeg: 動画処理としてpythonライブラリで使用。

#### サーバ
Nginx: リバースプロキシとして機能し、HTTP/HTTPSリクエストを Gunicorn に転送。\
AWS EC2: アプリケーションホスティングのための仮想サーバー。\
Let's Encrypt (Certbot): 無料のSSL証明書を取得し、HTTPSを有効化。


## 機能一覧
以下のリンクによって移動できる \
https://videoeditapp.yuta-kimu.com \

#### 実装した操作
- compress: MP4 をビットレート指定で圧縮
- change_resolution: 幅・高さ指定でスケール変更
- change_aspect_ratio: アスペクト比を 16:9 などに変更 (setdar, setsar)
- extract_audio: 音声のみ抽出 (MP3)
- create_gif: 一部区間を切り出し、GIF を生成
- create_webm: 一部区間を切り出し、WebM を生成

![image](https://github.com/user-attachments/assets/840db955-b70c-491a-a3c5-3ee2cc974cbc)

操作(operation)の欄(一番上の欄)でどの操作を行うかを選択することができる。

#### 分割アップロード

大きな動画ファイルをクライアント JavaScript で2MB毎に分割 (チャンク化) し、複数リクエストでサーバーへ送信
upload_chunk API で各チャンクを受け取り、一時ファイルとして保存
finalize_upload API で結合＆FFmpeg 処理 → 結果をダウンロード形式で返却

#### UI (HTML + JavaScript)

- シンプルなフォームで操作種類を選択し、動画をアップロード
- Chunk サイズ 2MB (デフォルト) で分割 → /upload_chunk へ送信
- 全チャンク送信後 /finalize_upload を呼んでサーバーで動画結合 & 変換
- 結果ファイルを Blob として受け取り、ダウンロード
- 処理状況もページ下部に表示

  
  ![スクリーンショット 2025-01-23 011539](https://github.com/user-attachments/assets/7a1aef3b-41d5-4e72-9d20-8e3377def90d)

  ![image](https://github.com/user-attachments/assets/792215ff-f43f-466a-8272-b9e6735bb617)


## 環境構築
1.FFMpegのインストール
```
sudo apt-get update
sudo apt-get install ffmpeg
ffmpeg -version  # 4.2 以上を想定
```
ffmpegはインストール先のパスを環境変数に指定する必要

##制限
- ファイルサイズ: 分割アップロードが可能だが、サーバー容量や FFmpeg のメモリ負荷にご注意。
- 音声が無い動画で extract_audio はエラーになるなど、特定操作で失敗するケースがある。
- aspect_ratio の「16:1」など極端な指定 はエラーになる可能性。
- サーバーの CORS 設定 は、同一ドメイン使用か、必要に応じて flask_cors など使う。


## 今後の展望
- フロントエンドのUI強化 (プログレスバー、ドラッグ＆ドロップ、デザインなど)
- 動画プレビュー機能
- 認証/ログイン実装
- さらなる変換オプション (回転、ビットレート選択、フィルターなど)

## 参考資料
- [Flask 公式ドキュメント](https://flask.palletsprojects.com/)
- [Gunicorn 公式ドキュメント](https://docs.gunicorn.org/)
- [Nginx 公式ドキュメント](https://nginx.org/en/docs/)
- [Certbot 公式サイト](https://certbot.eff.org/)
- [ffmpeg 公式サイト](https://ffmpeg.org/)


## まとめ
まとめ
- このリポジトリは、Flask + FFmpeg + 分割アップロード を組み合わせた 動画変換 Web サービス のサンプル実装です。
- Python + ffmpeg-python で簡易的な処理を書けるため、拡張が容易。
- systemd や Nginx を利用した本番運用も可能。
- ぜひフォークして、自由にカスタマイズしてください
