import { ChevronRight, Leaf, MapPin, Pencil, Plus, Trash2, X } from "lucide-react";
import { Empty } from "@/features/shared/empty";
import type { Customer, Design, Property } from "@/lib/api";

export function PropertiesView({
  customers,
  properties,
  designs,
  onAdd,
  onSelect,
}: {
  customers: Customer[];
  properties: Property[];
  designs: Design[];
  onAdd: () => void;
  onSelect: (property: Property) => void;
}) {
  const customerName = (id?: string | null) =>
    customers.find((row) => row.id === id)?.name || "Unassigned customer";
  return (
    <div className="content-stack">
      <div className="action-row">
        <button className="primary compact" onClick={onAdd}>
          <Plus />
          New property
        </button>
      </div>
      <section className="section-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow dark">Managed sites</p>
            <h2>
              {properties.length} propert{properties.length === 1 ? "y" : "ies"}
            </h2>
          </div>
        </div>
        {properties.length ? (
          <div className="property-grid">
            {properties.map((property) => (
              <button
                className="property-card"
                key={property.id}
                onClick={() => onSelect(property)}
              >
                <div className="property-icon">
                  <MapPin />
                </div>
                <div>
                  <h3>{property.name}</h3>
                  <p>{property.location || "No location added"}</p>
                  <span>
                    {customerName(property.customer_id)} ·{" "}
                    {
                      designs.filter(
                        (design) => design.property_id === property.id,
                      ).length
                    }{" "}
                    designs
                  </span>
                </div>
                <ChevronRight />
              </button>
            ))}
          </div>
        ) : (
          <Empty text="Add a property and connect it to a customer." />
        )}
      </section>
    </div>
  );
}

export function PropertyDetail({
  property,
  customer,
  designs,
  close,
  openDesign,
  edit,
  remove,
}: {
  property: Property;
  customer?: Customer;
  designs: Design[];
  close: () => void;
  openDesign: (id: string) => void;
  edit: () => void;
  remove: () => void;
}) {
  return (
    <div className="modal-backdrop" role="presentation">
      <section
        className="detail-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="property-detail-title"
      >
        <div className="modal-heading">
          <div>
            <p className="eyebrow dark">Property record</p>
            <h2 id="property-detail-title">{property.name}</h2>
          </div>
          <button
            className="icon-button dark"
            onClick={close}
            aria-label="Close"
          >
            <X />
          </button>
        </div>
        <div className="record-actions">
          <button className="secondary" onClick={edit}>
            <Pencil />
            Edit property
          </button>
          <button className="danger-button" onClick={remove}>
            <Trash2 />
            Delete
          </button>
        </div>
        <dl className="detail-list">
          <div>
            <dt>Location</dt>
            <dd>{property.location || "Not provided"}</dd>
          </div>
          <div>
            <dt>Customer</dt>
            <dd>{customer?.name || "Unassigned"}</dd>
          </div>
          <div>
            <dt>Designs</dt>
            <dd>{designs.length}</dd>
          </div>
        </dl>
        <div className="linked-heading">
          <h3>Attached designs</h3>
        </div>
        {designs.length ? (
          <div className="rows">
            {designs.map((design) => (
              <button
                className="design-row"
                key={design.id}
                onClick={() => openDesign(design.id)}
              >
                <span className="row-icon">
                  <Leaf />
                </span>
                <span>
                  <strong>{design.name}</strong>
                  <small>
                    {design.status} · {design.goal || "No brief"}
                  </small>
                </span>
                <ChevronRight />
              </button>
            ))}
          </div>
        ) : (
          <Empty text="No design projects are attached to this property." />
        )}
      </section>
    </div>
  );
}
