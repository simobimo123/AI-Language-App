import 'dart:typed_data';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';

class TtsPlayerService {
  final AudioPlayer _player = AudioPlayer();

  Future<void> play(Uint8List audioBytes) async {
    if (audioBytes.isEmpty) {
      throw StateError('TTS player received empty audio.');
    }

    _validateWav(audioBytes);

    try {
      await _player.stop();
      await _player.play(
        BytesSource(
          audioBytes,
          mimeType: 'audio/wav',
        ),
      );
      debugPrint(
        '[TTS][PLAYER] WAV playback started (${audioBytes.length} bytes).',
      );
    } catch (error, stackTrace) {
      debugPrint('[TTS][PLAYER] Playback failed: $error');
      debugPrintStack(stackTrace: stackTrace);
      rethrow;
    }
  }

  void _validateWav(Uint8List bytes) {
    if (bytes.length < 12) {
      throw StateError('TTS audio is too small to be a valid WAV file.');
    }

    final riff = String.fromCharCodes(bytes.sublist(0, 4));
    final wave = String.fromCharCodes(bytes.sublist(8, 12));

    if (riff != 'RIFF' || wave != 'WAVE') {
      throw StateError(
        'TTS server returned data that is not a valid WAV file.',
      );
    }
  }

  Future<void> stop() => _player.stop();

  Future<void> dispose() => _player.dispose();
}
