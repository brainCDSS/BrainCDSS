import 'package:flutter/material.dart';

class DraggableAssistantButton extends StatefulWidget {
  const DraggableAssistantButton({
    super.key,
    required this.onTap,
    required this.child,
    this.size = 72,
    this.edgePadding = 20,
  });

  final VoidCallback onTap;
  final Widget child;
  final double size;
  final double edgePadding;

  @override
  State<DraggableAssistantButton> createState() =>
      _DraggableAssistantButtonState();
}

class _DraggableAssistantButtonState extends State<DraggableAssistantButton> {
  double? _left;
  double? _top;
  double _maxLeft = 0;
  double _maxTop = 0;
  bool _didDrag = false;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          _maxLeft = (constraints.maxWidth - widget.size - widget.edgePadding)
              .clamp(widget.edgePadding, double.infinity)
              .toDouble();
          _maxTop = (constraints.maxHeight - widget.size - widget.edgePadding)
              .clamp(widget.edgePadding, double.infinity)
              .toDouble();
          final left = (_left ?? _maxLeft)
              .clamp(widget.edgePadding, _maxLeft)
              .toDouble();
          final top =
              (_top ?? _maxTop).clamp(widget.edgePadding, _maxTop).toDouble();

          return Stack(
            clipBehavior: Clip.none,
            children: [
              Positioned(
                left: left,
                top: top,
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () {
                    if (!_didDrag) {
                      widget.onTap();
                    }
                  },
                  onPanStart: (_) => _didDrag = false,
                  onPanUpdate: (details) {
                    if (details.delta.distanceSquared > 4) {
                      _didDrag = true;
                    }
                    setState(() {
                      final currentLeft = (_left ?? left)
                          .clamp(widget.edgePadding, _maxLeft)
                          .toDouble();
                      final currentTop = (_top ?? top)
                          .clamp(widget.edgePadding, _maxTop)
                          .toDouble();
                      _left = (currentLeft + details.delta.dx)
                          .clamp(widget.edgePadding, _maxLeft)
                          .toDouble();
                      _top = (currentTop + details.delta.dy)
                          .clamp(widget.edgePadding, _maxTop)
                          .toDouble();
                    });
                  },
                  child: SizedBox(
                    width: widget.size,
                    height: widget.size,
                    child: widget.child,
                  ),
                ),
              ),
            ],
          );
        },
      );
}
