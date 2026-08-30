import 'api_exception.dart';

class ErrorMessage {
  const ErrorMessage._();

  static String from(Object error) {
    if (error is ApiException) {
      return error.message;
    }

    final message = error.toString();

    if (message.startsWith('Exception: ')) {
      return message.substring('Exception: '.length);
    }

    return message;
  }
}
