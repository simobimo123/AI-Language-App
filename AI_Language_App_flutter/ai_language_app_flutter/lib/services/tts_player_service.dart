import 'dart:typed_data';

import 'package:audioplayers/audioplayers.dart';

class TtsPlayerService {
  final AudioPlayer _player = AudioPlayer();

  Future<void> play(Uint8List audioBytes) async {
    await _player.stop();
    await _player.play(BytesSource(audioBytes));
  }

  Future<void> stop() => _player.stop();

  Future<void> dispose() => _player.dispose();
}
