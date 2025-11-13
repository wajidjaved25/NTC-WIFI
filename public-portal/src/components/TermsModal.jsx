function TermsModal({ portalDesign, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title" style={{ color: portalDesign?.primary_color }}>
            Terms and Conditions
          </h2>
        </div>
        <div
          className="modal-body"
          dangerouslySetInnerHTML={{ __html: portalDesign?.terms_text }}
        />
        <div className="modal-footer">
          <button
            className="btn btn-primary"
            onClick={onClose}
            style={{ background: portalDesign?.primary_color }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default TermsModal;
