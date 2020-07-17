import { Component, OnInit } from '@angular/core';
import { StateService } from '../state.service';

@Component({
  selector: 'app-loader-overlay',
  templateUrl: './loader-overlay.component.html',
  styleUrls: ['./loader-overlay.component.scss']
})
export class LoaderOverlayComponent implements OnInit {

  constructor(public state: StateService) { }

  ngOnInit() {
  }

}
