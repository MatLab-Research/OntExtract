@experiments_bp.route('/<int:experiment_id>/document/<int:document_id>/run_tools', methods=['POST'])
@api_require_login_for_write
def run_processing_tools(experiment_id, document_id):
    """
    Execute processing tools on a document (manual mode).

    Request body:
    {
        "tools": ["segment_paragraph", "segment_sentence"]
    }

    Returns:
    {
        "success": true,
        "results": [
            {
                "tool_name": "segment_paragraph",
                "status": "success",
                "data": [...],
                "metadata": {...},
                "provenance": {...}
            }
        ]
    }
    """
    try:
        from app.services.processing_tools import DocumentProcessor
        from app.services.tool_registry import validate_tool_strategy
        from app import db

        # Get experiment and document
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        exp_doc = ExperimentDocument.query.filter_by(
            experiment_id=experiment_id,
            document_id=document_id
        ).first_or_404()
        document = exp_doc.document

        # Get requested tools
        data = request.json
        tool_names = data.get('tools', [])

        if not tool_names:
            return jsonify({
                "success": False,
                "error": "No tools specified"
            }), 400

        # Validate tools
        validation = validate_tool_strategy({str(document_id): tool_names})
        if not validation['valid']:
            return jsonify({
                "success": False,
                "error": "Tool validation failed",
                "warnings": validation['warnings']
            }), 400

        # Initialize processor
        processor = DocumentProcessor(
            user_id=current_user.id,
            experiment_id=experiment_id
        )

        # Execute tools
        results = []
        for tool_name in tool_names:
            if hasattr(processor, tool_name):
                tool_func = getattr(processor, tool_name)
                result = tool_func(document.get_text_content())
                results.append(result.to_dict())

                # Store result in database
                processing_record = ExperimentDocumentProcessing(
                    experiment_document_id=exp_doc.id,
                    processing_type=tool_name,
                    status='completed' if result.status == 'success' else 'error',
                    result_data=result.to_dict(),
                    created_by=current_user.id
                )
                db.session.add(processing_record)
            else:
                results.append({
                    "tool_name": tool_name,
                    "status": "error",
                    "error": f"Tool '{tool_name}' not found"
                })

        db.session.commit()

        return jsonify({
            "success": True,
            "results": results,
            "tool_count": len(results),
            "validation": validation
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error running tools: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


