import update_rh from "./rh.js";
import update_convention from "./convention.js";
import update_avenant from "./avenant.js";
import update_pi_logiciel from "./pi_logiciel.js";
import update_pi_invention from "./pi_invention.js";
import update_autre_demande from "./autre_demande.js";

export default function update_form(form, model) {
  const dispatch_table = {
    rh: update_rh,
    convention: update_convention,
    avenant_convention: update_avenant,
    pi_logiciel: update_pi_logiciel,
    pi_invention: update_pi_invention,
    autre: update_autre_demande,
  };
  dispatch_table[form.name](form, model);
}
