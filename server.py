import os
import uuid
import logging
import ffmpeg
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

app = Flask(__name__)
CORS(app)  # 必要に応じてCORS許可

# 最大リクエストサイズを設定 (例: 100MB)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

# エラーハンドラを追加 (オプション)
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"status": "error", "message": "Uploaded file is too large"}), 413


UPLOAD_DIR = 'uploads'
PROCESSED_DIR = 'processed_files'
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# 必要パラメータの定義
REQUIRED_PARAMS = {
    "change_resolution": ["width", "height"],
    "change_aspect_ratio": ["aspect_ratio"],
    "create_gif": ["start_time", "duration"],
    "create_webm": ["start_time", "duration"],
    # 'compress' と 'extract_audio' は追加パラメータ不要
}

# チャンクアップロードAPI

@app.route('/upload_chunk', methods=['POST'])
def upload_chunk():
    """
    1つのチャンクを受け取り、UPLOAD_DIR に一時ファイルとして保存する。
    フロントが送る項目:
      - upload_id: (必須) 同じアップロードセッションを識別するID
      - chunk_index: (必須) 0,1,2,... の連番
      - file_chunk: (必須) 実際のバイナリチャンク
    例外:
      - file_chunk が届いていない or upload_id 等がない -> 400
    """
    upload_id = request.form.get("upload_id")
    chunk_index = request.form.get("chunk_index", type=int)
    file_chunk = request.files.get("file_chunk")
    if not (upload_id and chunk_index is not None and file_chunk):
        return jsonify({"status": "error", "message": "Missing chunk parameters"}), 400

    # 保存ファイル名: {upload_id}_{chunk_index}.part
    chunk_filename = f"{upload_id}_{chunk_index}.part"
    chunk_path = os.path.join(UPLOAD_DIR, chunk_filename)
    file_chunk.save(chunk_path)

    logging.info(f"Received chunk {chunk_index} for upload_id={upload_id}, size={file_chunk.content_length}")
    return jsonify({"status": "ok", "message": f"chunk {chunk_index} saved"}), 200

########################
# 2) finalize_upload + ffmpeg処理
########################
@app.route('/finalize_upload', methods=['POST'])
def finalize_upload():
    """
    全チャンクを受け取り終えた後に呼ばれる:
      - upload_id (必須)
      - total_chunks (必須)
      - file_name (任意だが拡張子判定等で使う)
      - operation, width, height, aspect_ratio, start_time, duration ... (ffmpeg向け)
    ここで:
      1) すべての .part ファイルを結合して1つの入力ファイルを作成
      2) ffmpeg で変換 (operation に応じた処理)
      3) 変換後ファイルを send_file でバイナリとして返す
    """

    upload_id = request.form.get("upload_id")
    total_chunks = request.form.get("total_chunks", type=int)
    file_name = request.form.get("file_name") or "uploaded.mp4"
    operation = request.form.get("operation", "compress")
    width = request.form.get("width", type=int)
    height = request.form.get("height", type=int)
    aspect_ratio = request.form.get("aspect_ratio")
    start_time = request.form.get("start_time", type=float)
    duration = request.form.get("duration", type=float)

    if not upload_id or not total_chunks:
        return jsonify({"status": "error", "message": "Missing finalize params"}), 400

    # 1) チャンク結合
    merged_filename = f"merged_{uuid.uuid4()}_{file_name}"
    merged_path = os.path.join(PROCESSED_DIR, merged_filename)

    with open(merged_path, 'wb') as merged_f:
        for i in range(total_chunks):
            chunk_path = os.path.join(UPLOAD_DIR, f"{upload_id}_{i}.part")
            if not os.path.exists(chunk_path):
                return jsonify({"status": "error", "message": f"Missing chunk {i}"}), 400
            with open(chunk_path, 'rb') as c:
                merged_f.write(c.read())
            os.remove(chunk_path)

    # 2) ffmpeg 変換
    try:
        output_path = process_video(merged_path, operation,
                                    width, height, aspect_ratio,
                                    start_time, duration)
    except Exception as e:
        logging.error(f"FFmpeg Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        # 元の結合ファイルは不要なら削除
        if os.path.exists(merged_path):
            os.remove(merged_path)

    # 3) 変換後ファイルをダウンロード形式で返す
    # 大容量の場合、send_file するとメモリ使用が大きくなる点に注意
    filename_for_download = f"converted_{os.path.basename(output_path)}"
    return send_file(
        output_path,
        as_attachment=True,
        download_name=filename_for_download
    )


def process_video(input_path, operation, width=None, height=None, aspect_ratio=None,
                  start_time=None, duration=None):
    """
    ffmpegを用いて、operationに応じた処理を行う。
    成功したら output_path を返す
    """
    # 拡張子のマッピング
    ext_map = {
        'extract_audio': '.mp3',
        'create_gif': '.gif',
        'create_webm': '.webm',
    }
    output_ext = ext_map.get(operation, '.mp4')

    output_path = os.path.join(PROCESSED_DIR, f"processed_{uuid.uuid4()}{output_ext}")

    if operation == 'compress':
        (
            ffmpeg
            .input(input_path)
            .output(output_path, video_bitrate='500k')
            .run(cmd='/usr/bin/ffmpeg', overwrite_output=True)
        )
    elif operation == 'change_resolution':
        if not width or not height:
            raise ValueError('Width/height required for change_resolution')
        (
            ffmpeg
            .input(input_path)
            .filter('scale', width, height)
            .output(output_path)
            .run(overwrite_output=True)
        )
    elif operation == 'change_aspect_ratio':
        if not aspect_ratio:
            raise ValueError('aspect_ratio required for change_aspect_ratio')
        (
            ffmpeg
            .input(input_path)
            .filter('setsar', '1')
            .filter('setdar', aspect_ratio)
            .output(output_path)
            .run(overwrite_output=True)
        )
    elif operation == 'extract_audio':
        (
            ffmpeg
            .input(input_path)
            .output(output_path, format='mp3', acodec='libmp3lame', ab='192k')
            .run(overwrite_output=True)
        )
    elif operation == 'create_gif':
        if start_time is None or duration is None:
            raise ValueError('start_time/duration required for create_gif')
        (
            ffmpeg
            .input(input_path, ss=start_time, t=duration)
            .output(output_path, vf='fps=10,scale=320:-1:flags=lanczos')
            .run(overwrite_output=True)
        )
    elif operation == 'create_webm':
        if start_time is None or duration is None:
            raise ValueError('start_time/duration required for create_webm')
        (
            ffmpeg
            .input(input_path, ss=start_time, t=duration)
            .output(output_path, format='webm')
            .run(overwrite_output=True)
        )
    else:
        raise ValueError('Unsupported operation')

    logging.info(f"FFmpeg done: {operation}, output={output_path}")
    return output_path


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
