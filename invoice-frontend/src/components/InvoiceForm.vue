<template>
  <div class="invoice-form">
    <h1>Create Invoice</h1>

    <!-- Customer Information -->
    <div class="card">
      <h2>Customer Information</h2>
      <div class="field">
        <label>Customer Sold to:</label>
        <input type="text" v-model="customer_name" placeholder="Enter customer name"/>
      </div>
      <div class="field">
        <label>Customer Address:</label>
        <input type="text" v-model="customer_address" placeholder="Enter customer address"/>
      </div>
      <div class="field">
        <label>Customer Contract No:</label>
        <input type="text" v-model="contract_no" placeholder="Enter contract number"/>
      </div>
      <div class="field">
        <label>Customer PO No:</label>
        <input type="text" v-model="po_no" placeholder="Enter PO number"/>
      </div>
    </div>

    <!-- Items Table -->
    <div class="card">
      <h2>Invoice Items</h2>
      <table>
        <thead>
          <tr>
            <th>Description</th>
            <th>Unit</th>
            <th>Qty</th>
            <th>Unit Rate</th>
            <th>Amount</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, index) in items" :key="index" :class="{ focused: focusedRow === index }" @focusin="focusedRow = index" @focusout="focusedRow = null">
            <td><input type="text" v-model="item.description" placeholder="Item description"/></td>
            <td><input type="text" v-model="item.unit" placeholder="Unit"/></td>
            <td><input type="number" v-model.number="item.qty"/></td>
            <td><input type="number" v-model.number="item.unit_rate"/></td>
            <td>{{ formatCurrency(item.qty * item.unit_rate) }}</td>
            <td><button class="btn-remove" @click="removeItem(index)">Remove</button></td>
          </tr>
        </tbody>
      </table>
      <button class="btn-add" @click="addItem">+ Add Item</button>
    </div>

    <!-- Totals -->
    <div class="totals card">
      <p>Subtotal: <span>{{ formatCurrency(subtotal) }}</span></p>
      <p>VAT (7.5%): <span>{{ formatCurrency(vat) }}</span></p>
      <p>Total: <span>{{ formatCurrency(total) }}</span></p>
    </div>

    <!-- Actions -->
    <div class="actions">
      <button class="btn-submit" @click="submitInvoice">Submit Invoice</button>
      <button class="btn-reset" @click="resetForm">Reset Form</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import axios from 'axios';

// Customer fields
const customer_name = ref("");
const customer_address = ref("");
const contract_no = ref("");
const po_no = ref("");

// Items
const items = ref([{ description: "", unit: "", qty: 1, unit_rate: 0 }]);

// Highlight focused row
const focusedRow = ref<number | null>(null);

// Methods to add/remove items
function addItem() {
  items.value.push({ description: "", unit: "", qty: 1, unit_rate: 0 });
}

function removeItem(index: number) {
  items.value.splice(index, 1);
}

// Computed totals
const subtotal = computed(() => items.value.reduce((sum, i) => sum + i.qty * i.unit_rate, 0));
const vat = computed(() => subtotal.value * 0.075);
const total = computed(() => subtotal.value + vat.value);

// Format currency
function formatCurrency(value: number) {
  return value.toLocaleString("en-NG", { style: "currency", currency: "NGN" });
}

// Submit function
async function submitInvoice() {
  const invoiceData = {
    invoice_no: "INV-0001",
    invoice_date: new Date().toISOString().split("T")[0],
    vat_date: new Date().toISOString().split("T")[0],
    customer_name: customer_name.value,
    customer_address: customer_address.value,
    contract_no: contract_no.value,
    po_no: po_no.value,
    items: items.value.map(item => ({
      description: item.description,
      unit: item.unit,
      qty: item.qty,
      unit_rate: item.unit_rate
    })),
    subtotal: subtotal.value,
    vat: vat.value,
    total: total.value
  };

  try {
    const response = await axios.post("http://127.0.0.1:8000/api/save-invoice/", invoiceData);
    alert("Invoice submitted successfully!");
    console.log(response.data);
  } catch (err) {
    console.error(err);
    alert("Error submitting invoice.");
  }
}

// Reset form
function resetForm() {
  customer_name.value = "";
  customer_address.value = "";
  contract_no.value = "";
  po_no.value = "";
  items.value = [{ description: "", unit: "", qty: 1, unit_rate: 0 }];
}
</script>

<style scoped>
.invoice-form {
  max-width: 900px;
  margin: 2rem auto;
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
  padding: 0 1rem;
}

h1 {
  text-align: center;
  margin-bottom: 2rem;
  color: #2c3e50;
}

.card {
  background: #ffffff;
  padding: 1.5rem;
  margin-bottom: 2rem;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

h2 {
  margin-bottom: 1rem;
  color: #34495e;
}

.field {
  margin-bottom: 1rem;
}

.field label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.3rem;
  color: #2c3e50;
}

input[type="text"], input[type="number"] {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 5px;
  transition: border 0.2s;
}

input:focus {
  border-color: #3498db;
  outline: none;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1rem;
}

th, td {
  border: 1px solid #ddd;
  padding: 0.5rem;
  text-align: left;
}

th {
  background: #f4f4f4;
  font-weight: 600;
}

tr.focused {
  background-color: #f0f8ff;
}

.btn-add, .btn-remove, .btn-submit, .btn-reset {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.2s;
  margin-top: 0.5rem;
}

.btn-add {
  background-color: #2ecc71;
  color: white;
}

.btn-add:hover {
  background-color: #27ae60;
}

.btn-remove {
  background-color: #e74c3c;
  color: white;
}

.btn-remove:hover {
  background-color: #c0392b;
}

.btn-submit {
  width: 48%;
  background-color: #3498db;
  color: white;
  font-size: 1.1rem;
  margin-right: 4%;
}

.btn-submit:hover {
  background-color: #2980b9;
}

.btn-reset {
  width: 48%;
  background-color: #95a5a6;
  color: white;
  font-size: 1.1rem;
}

.btn-reset:hover {
  background-color: #7f8c8d;
}

.totals p {
  text-align: right;
  font-size: 1.1rem;
  margin: 0.5rem 0;
}

.totals span {
  font-weight: bold;
  color: #2c3e50;
}

.actions {
  display: flex;
  justify-content: space-between;
  margin-bottom: 2rem;
}
</style>
