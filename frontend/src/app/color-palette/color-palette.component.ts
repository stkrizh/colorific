import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';
import { DomSanitizer, SafeStyle } from "@angular/platform-browser";
import { Color } from "../types";


@Component({
  selector: 'app-color-palette',
  templateUrl: './color-palette.component.html',
  styleUrls: ['./color-palette.component.scss']
})
export class ColorPaletteComponent implements OnInit {

  @Input() colors: Array<Color>;
  @Output() colorSelected = new EventEmitter<Color>();

  constructor(private _sanitizer: DomSanitizer,) { }

  ngOnInit() {
  }

  convertColorToBackground(color: Color): SafeStyle {
    return this._sanitizer.bypassSecurityTrustStyle(
      `rgb(${color.red}, ${color.green}, ${color.blue})`
    )
  }

  getColorInfo(color: Color): string {
    let prefix = color.name === null ? '' : `${color.name} - `;
    return `${prefix}#${color.toHex()} - ${(color.percentage * 100).toFixed(1)}%`;
  }

  selectColor(color: Color) {
    this.colorSelected.emit(color);
  }
}
