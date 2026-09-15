import 'package:flutter/material.dart';

import '../services/api/api_service.dart';
import '../services/tts_player_service.dart';

class TtsTestPage extends StatefulWidget {
  const TtsTestPage({super.key});

  @override
  State<TtsTestPage> createState() => _TtsTestPageState();
}

class _TtsTestPageState extends State<TtsTestPage> {
  final ApiService _api = ApiService();
  final TtsPlayerService _player = TtsPlayerService();

  static const _testText = 'Hello, this is a voice test.';

  bool _loading = false;
  String _status = 'Ready to test TTS.';

  Future<void> _playTestVoice() async {
    if (_loading) {
      return;
    }

    setState(() {
      _loading = true;
      _status = 'Generating and playing voice...';
    });

    try {
      final audio = await _api.synthesizeSpeech(
        text: _testText,
        learningLanguage: 'en',
        nativeLanguage: 'ar',
        gender: 'female',
      );

      await _player.play(
        audio as dynamic,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _status = 'Audio playback started successfully.';
      });
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _status = 'TTS test failed: $error';
      });
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('TTS Test'),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(
                Icons.volume_up_rounded,
                size: 64,
              ),
              const SizedBox(height: 20),
              const Text(
                _testText,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 28),
              FilledButton.icon(
                onPressed: _loading ? null : _playTestVoice,
                icon: _loading
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.play_arrow_rounded),
                label: Text(_loading ? 'Please wait...' : 'Play voice'),
              ),
              const SizedBox(height: 20),
              Text(
                _status,
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
