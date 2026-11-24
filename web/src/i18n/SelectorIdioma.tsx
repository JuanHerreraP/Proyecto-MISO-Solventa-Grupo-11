import { useTranslation } from "react-i18next";

import { cambiarIdioma, IDIOMAS, type Idioma } from ".";

type Props = {
  className?: string;
};

/** Selector de idioma de la interfaz; el nombre de cada idioma se muestra en su propio idioma. */
export default function SelectorIdioma({ className }: Props) {
  const { t, i18n } = useTranslation();
  const actual = (IDIOMAS as readonly string[]).includes(i18n.language) ? i18n.language : "es";

  return (
    <label className={["selector-idioma", className].filter(Boolean).join(" ")}>
      <span className="material-symbols-outlined" aria-hidden="true">language</span>
      <span className="selector-idioma-texto">{t("idioma.etiqueta")}</span>
      <select
        value={actual}
        onChange={(evento) => void cambiarIdioma(evento.target.value as Idioma)}
      >
        {IDIOMAS.map((idioma) => (
          <option key={idioma} value={idioma} lang={idioma}>
            {t(`idioma.nombre.${idioma}`)}
          </option>
        ))}
      </select>
    </label>
  );
}
