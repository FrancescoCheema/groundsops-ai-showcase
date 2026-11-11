import { Building2, ChevronRight, MapPin, Pencil, Plus, Trash2, X } from "lucide-react";
import { Empty } from "@/features/shared/empty";
import { plural } from "@/features/shared/format";
import type { Customer, Property } from "@/lib/api";

export function CustomersView({
  customers,
  properties,
  onAdd,
  onSelect,
}: {
  customers: Customer[];
  properties: Property[];
  onAdd: (value: "customer" | "property" | "design" | null) => void;
  onSelect: (customer: Customer) => void;
}) {
  return (
    <div className="content-stack">
      <div className="action-row">
        <button className="secondary" onClick={() => onAdd("property")}>
          <Building2 />
          Add property
        </button>
        <button className="primary compact" onClick={() => onAdd("customer")}>
          <Plus />
          New customer
        </button>
      </div>
      <section className="section-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow dark">Directory</p>
            <h2>
              {customers.length} customer{customers.length === 1 ? "" : "s"}
            </h2>
          </div>
        </div>
        {customers.length ? (
          <div className="customer-grid">
            {customers.map((customer) => (
              <button
                className="customer-card"
                key={customer.id}
                onClick={() => onSelect(customer)}
              >
                <div className="initial">{customer.name.charAt(0)}</div>
                <div>
                  <h3>{customer.name}</h3>
                  <p>
                    {customer.email || customer.phone || "No contact details"}
                  </p>
                  <span>
                    {plural(
                      properties.filter(
                        (site) => site.customer_id === customer.id,
                      ).length,
                      "property",
                      "properties",
                    )}
                  </span>
                </div>
                <ChevronRight />
              </button>
            ))}
          </div>
        ) : (
          <Empty text="Add your first customer, then connect a property." />
        )}
      </section>
    </div>
  );
}

export function CustomerDetail({
  customer,
  properties,
  close,
  openProperty,
  edit,
  remove,
}: {
  customer: Customer;
  properties: Property[];
  close: () => void;
  openProperty: (property: Property) => void;
  edit: () => void;
  remove: () => void;
}) {
  return (
    <div className="modal-backdrop" role="presentation">
      <section
        className="detail-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="customer-detail-title"
      >
        <div className="modal-heading">
          <div>
            <p className="eyebrow dark">Customer record</p>
            <h2 id="customer-detail-title">{customer.name}</h2>
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
            Edit customer
          </button>
          <button className="danger-button" onClick={remove}>
            <Trash2 />
            Delete
          </button>
        </div>
        <dl className="detail-list">
          <div>
            <dt>Email</dt>
            <dd>{customer.email || "Not provided"}</dd>
          </div>
          <div>
            <dt>Phone</dt>
            <dd>{customer.phone || "Not provided"}</dd>
          </div>
          <div>
            <dt>Properties</dt>
            <dd>{properties.length}</dd>
          </div>
        </dl>
        <div className="linked-heading">
          <h3>Attached properties</h3>
        </div>
        {properties.length ? (
          <div className="rows">
            {properties.map((property) => (
              <button
                className="design-row"
                key={property.id}
                onClick={() => openProperty(property)}
              >
                <span className="row-icon">
                  <MapPin />
                </span>
                <span>
                  <strong>{property.name}</strong>
                  <small>{property.location || "No location"}</small>
                </span>
                <ChevronRight />
              </button>
            ))}
          </div>
        ) : (
          <Empty text="No properties are attached to this customer." />
        )}
      </section>
    </div>
  );
}
