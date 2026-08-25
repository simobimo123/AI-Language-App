import 'package:google_sign_in/google_sign_in.dart';

class GoogleAuthService {
  static const String serverClientId =
      '1037381279399-hni83i4bgc9pvfa4dnreqb0ibjsvlbre.apps.googleusercontent.com';

  final GoogleSignIn _googleSignIn = GoogleSignIn.instance;

  bool _initialized = false;

  Future<void> _initialize() async {
    if (_initialized) {
      return;
    }

    await _googleSignIn.initialize(serverClientId: serverClientId);

    _initialized = true;
  }

  Future<String?> signInAndGetIdToken() async {
    await _initialize();

    try {
      final account = await _googleSignIn.authenticate();

      final idToken = account.authentication.idToken;

      if (idToken == null || idToken.isEmpty) {
        throw Exception('Google did not return an ID token');
      }

      return idToken;
    } on GoogleSignInException {
      rethrow;
    }
  }

  Future<void> signOut() async {
    await _initialize();

    await _googleSignIn.signOut();
  }
}
