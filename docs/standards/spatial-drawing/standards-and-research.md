# Standards and interaction research observations

Reviewed 2026-10-03. These are original factual summaries and design inferences,
not copied implementation, normative adoption or executed runtime evidence.

## W3C Web Annotation

Primary source: https://www.w3.org/TR/2017/REC-annotation-model-20170223/
(dated Recommendation; full text fetched). Sections 3 and 4 distinguish the
annotation, its body and its target, with selectors and resource states for more
specific references. Section 4.2.7's SVG selector describes an area relative to
its source resource; it does not specify a general XR coordinate or anchor
contract. The model separates representation from transport.

Foundry inference: an annotation binding should refer to a host-owned target and
revision independently of stroke geometry. A target that disappears or changes
must produce an explicit unresolved binding, not silently reattach to another
scene object. Do not adopt JSON-LD, a web protocol, a universal selector model or
an XR-compliance claim merely because this source is normative. Documentation
facts only; W3C publication terms apply, no implementation or figures copied.

## W3C InkML

Primary source: https://www.w3.org/TR/2011/REC-InkML-20110920/
(dated Recommendation; full text fetched). Section 3.1.2 defines channels with
dimension, units and interpretation: Z is height above the writing surface.
Section 6.1 distinguishes channel mappings from canvas transformations.

Foundry inference: capture channel semantics and conversion explicitly; a field
named Z is insufficient proof of interchangeable 3D coordinate conventions.
Keep import/export optional and loss-reporting. Neither an InkML codec nor full
conformance is proposed for the first experiment. This supplements the existing
manifest observation, not another independent implementation lineage.

## Yjs selective undo

Primary source: https://docs.yjs.dev/api/undo-manager
(full current documentation fetched 2026-10-03; mutable documentation, no
implementation pin reviewed here). UndoManager can scope captured operations to
shared types and transaction origins, group changes by capture timeout, and
break groups with stopCapturing.

Foundry inference: collaboration needs an explicit answer to whose operation is
undone and what constitutes an edit. A local revision guard or local undo stack
does not supply distributed convergence, authorization or user-scoped undo.
Use as a design counterexample, not mandatory stroke-Core evidence, a selected
dependency or a claim of tested network behavior. No source or assets copied.

## VRSketchIn

Primary author-hosted paper: https://www.uni-ulm.de/fileadmin/website_uni_ulm/iui.inst.100/institut/Papers/Prof_Rukzio/2020/VRSketchIn_Tobias_Drey.pdf
DOI 10.1145/3313831.3376628, CHI 2020. Full 14-page PDF fetched. The paper combines
tracked-pen free-space drawing with pen/tablet surface drawing. Its design space
uses interviews with ten experts; the prototype walkthrough uses six participants
from convenience sampling. Pages 8–10 discuss precision concerns and extra steps
needed to reach constrained drawing. Those observations are not a general
performance or comfort guarantee for current headsets.

Foundry inference: the first input experiment should compare the same document
operations driven by free-space samples and constrained-plane samples, with an
explicit mode transition and preview cancellation. Keep selection/projection and
device policy outside the document. The paper is interaction research, not a
maintained reusable source library. Page 1 gives author/ACM rights and permissions;
no code, figures, icons, assets or paper text are copied.

SymbiosisSketch's Autodesk-hosted PDF was located but direct full-text retrieval
failed. It is not counted as additional reviewed evidence or a source-gate pass.
